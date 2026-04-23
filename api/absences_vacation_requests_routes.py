"""Vacation requests API routes."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_auth, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/vacationrequests')
def get_vacation_requests(request: Request):
    """Get all vacation requests or pending ones"""
    status_filter = request.query_params.get('status')
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if status_filter == 'pending':
        cursor.execute("""
            SELECT vr.*, e.Vorname, e.Name, e.TeamId
            FROM VacationRequests vr
            JOIN Employees e ON vr.EmployeeId = e.Id
            WHERE vr.Status = 'InBearbeitung'
            ORDER BY vr.CreatedAt DESC
        """)
    else:
        cursor.execute("""
            SELECT vr.*, e.Vorname, e.Name, e.TeamId
            FROM VacationRequests vr
            JOIN Employees e ON vr.EmployeeId = e.Id
            ORDER BY vr.CreatedAt DESC
        """)
    
    requests = []
    for row in cursor.fetchall():
        requests.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': row['Status'],
            'notes': row['Notes'],
            'disponentResponse': row['DisponentResponse'],
            'createdAt': row['CreatedAt'],
            'processedAt': row['ProcessedAt']
        })
    
    conn.close()
    return requests


@router.post('/api/vacationrequests', dependencies=[Depends(require_auth), Depends(check_csrf)])
def create_vacation_request(request: Request, data: dict = Depends(parse_json_body)):
    """Create new vacation request"""
    try:
        if not data.get('employeeId') or not data.get('startDate') or not data.get('endDate'):
            return JSONResponse(content={'error': 'EmployeeId, StartDate und EndDate sind erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO VacationRequests 
            (EmployeeId, StartDate, EndDate, Status, Notes, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, 'InBearbeitung', ?, ?, ?)
        """, (
            data.get('employeeId'),
            data.get('startDate'),
            data.get('endDate'),
            data.get('notes'),
            datetime.utcnow().isoformat(),
            request.session.get('user_email')
        ))
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': request_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create vacation request error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/vacationrequests/{id}/status', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_vacation_request_status(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update vacation request status (Admin only)"""
    try:
        status = data.get('status')
        response = data.get('response')
        
        if status not in ['Genehmigt', 'Abgelehnt', 'InBearbeitung']:
            return JSONResponse(content={'error': 'Ungültiger Status'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE VacationRequests 
            SET Status = ?, DisponentResponse = ?, ProcessedAt = ?, ProcessedBy = ?
            WHERE Id = ?
        """, (
            status,
            response,
            datetime.utcnow().isoformat(),
            request.session.get('user_email'),
            id
        ))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update vacation request error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/vacationrequests/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_vacation_request(request: Request, id: int):
    """Delete vacation request (Admin only) - allows cancellation of approved requests"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get request info for audit log
        cursor.execute("""
            SELECT vr.EmployeeId, vr.StartDate, vr.EndDate, vr.Status, e.Vorname, e.Name
            FROM VacationRequests vr
            JOIN Employees e ON vr.EmployeeId = e.Id
            WHERE vr.Id = ?
        """, (id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Urlaubsantrag nicht gefunden'}, status_code=404)
        
        employee_name = f"{row['Vorname']} {row['Name']}"
        status = row['Status']
        
        # Delete the vacation request
        cursor.execute("DELETE FROM VacationRequests WHERE Id = ?", (id,))
        
        # Log audit before commit
        changes = json.dumps({
            'employeeName': employee_name,
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': status
        }, ensure_ascii=False)
        log_audit(conn, 'VacationRequest', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete vacation request error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)

