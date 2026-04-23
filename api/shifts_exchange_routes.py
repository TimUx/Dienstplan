"""Shift exchange (Diensttausch) API routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_auth, require_role, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# SHIFT EXCHANGE ENDPOINTS
# ============================================================================

@router.get('/api/shiftexchanges/available')

def get_available_shift_exchanges(request: Request):
    """Get available shift exchanges"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT se.*, 
               sa.Date, sa.ShiftTypeId,
               st.Code as ShiftCode, st.Name as ShiftName,
               e.Vorname, e.Name, e.TeamId
        FROM ShiftExchanges se
        JOIN ShiftAssignments sa ON se.ShiftAssignmentId = sa.Id
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        JOIN Employees e ON se.OfferingEmployeeId = e.Id
        WHERE se.Status = 'Angeboten'
        ORDER BY sa.Date
    """)
    
    exchanges = []
    for row in cursor.fetchall():
        exchanges.append({
            'id': row['Id'],
            'shiftAssignmentId': row['ShiftAssignmentId'],
            'offeringEmployeeId': row['OfferingEmployeeId'],
            'offeringEmployeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'date': row['Date'],
            'shiftCode': row['ShiftCode'],
            'shiftName': row['ShiftName'],
            'status': row['Status'],
            'offeringReason': row['OfferingReason'],
            'createdAt': row['CreatedAt']
        })
    
    conn.close()
    return exchanges


@router.get('/api/shiftexchanges/pending', dependencies=[Depends(require_role('Admin'))])

def get_pending_shift_exchanges(request: Request):
    """Get pending shift exchanges (Admin only)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT se.*, 
               sa.Date, sa.ShiftTypeId,
               st.Code as ShiftCode, st.Name as ShiftName,
               e1.Vorname as OfferingVorname, e1.Name as OfferingName,
               e2.Vorname as RequestingVorname, e2.Name as RequestingName
        FROM ShiftExchanges se
        JOIN ShiftAssignments sa ON se.ShiftAssignmentId = sa.Id
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        JOIN Employees e1 ON se.OfferingEmployeeId = e1.Id
        LEFT JOIN Employees e2 ON se.RequestingEmployeeId = e2.Id
        WHERE se.Status = 'Angefragt'
        ORDER BY sa.Date
    """)
    
    exchanges = []
    for row in cursor.fetchall():
        exchanges.append({
            'id': row['Id'],
            'shiftAssignmentId': row['ShiftAssignmentId'],
            'offeringEmployeeId': row['OfferingEmployeeId'],
            'offeringEmployeeName': f"{row['OfferingVorname']} {row['OfferingName']}",
            'requestingEmployeeId': row['RequestingEmployeeId'],
            'requestingEmployeeName': f"{row['RequestingVorname']} {row['RequestingName']}" if row['RequestingEmployeeId'] else None,
            'date': row['Date'],
            'shiftCode': row['ShiftCode'],
            'shiftName': row['ShiftName'],
            'status': row['Status'],
            'offeringReason': row['OfferingReason'],
            'createdAt': row['CreatedAt']
        })
    
    conn.close()
    return exchanges


@router.post('/api/shiftexchanges', dependencies=[Depends(require_auth), Depends(check_csrf)])

def create_shift_exchange(request: Request, data: dict = Depends(parse_json_body)):
    """Create new shift exchange offer"""
    try:
        
        if not data.get('shiftAssignmentId') or not data.get('offeringEmployeeId'):
            return JSONResponse(content={'error': 'ShiftAssignmentId und OfferingEmployeeId sind erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ShiftExchanges 
            (ShiftAssignmentId, OfferingEmployeeId, Status, OfferingReason, CreatedAt)
            VALUES (?, ?, 'Angeboten', ?, ?)
        """, (
            data.get('shiftAssignmentId'),
            data.get('offeringEmployeeId'),
            data.get('offeringReason'),
            datetime.utcnow().isoformat()
        ))
        
        exchange_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': exchange_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create shift exchange error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.post('/api/shiftexchanges/{id:int}/request', dependencies=[Depends(require_auth), Depends(check_csrf)])

def request_shift_exchange(request: Request, id, data: dict = Depends(parse_json_body)):
    """Request a shift exchange"""
    try:
        requesting_employee_id = data.get('requestingEmployeeId')
        
        if not requesting_employee_id:
            return JSONResponse(content={'error': 'RequestingEmployeeId ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ShiftExchanges 
            SET RequestingEmployeeId = ?, Status = 'Angefragt'
            WHERE Id = ? AND Status = 'Angeboten'
        """, (requesting_employee_id, id))
        
        if cursor.rowcount == 0:
            conn.close()
            return JSONResponse(content={'error': 'Tauschangebot nicht verfügbar'}, status_code=404)
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Request shift exchange error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Anfragen: {str(e)}'}, status_code=500)


@router.put('/api/shiftexchanges/{id:int}/process', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def process_shift_exchange(request: Request, id, data: dict = Depends(parse_json_body)):
    """Process shift exchange (approve/reject)"""
    try:
        status = data.get('status')
        notes = data.get('notes')
        
        if status not in ['Genehmigt', 'Abgelehnt']:
            return JSONResponse(content={'error': 'Status muss Genehmigt oder Abgelehnt sein'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get exchange details
        cursor.execute("""
            SELECT ShiftAssignmentId, OfferingEmployeeId, RequestingEmployeeId
            FROM ShiftExchanges
            WHERE Id = ? AND Status = 'Angefragt'
        """, (id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Tauschangebot nicht gefunden oder bereits bearbeitet'}, status_code=404)
        
        shift_assignment_id = row['ShiftAssignmentId']
        requesting_employee_id = row['RequestingEmployeeId']
        
        # Update exchange status
        cursor.execute("""
            UPDATE ShiftExchanges 
            SET Status = ?, DisponentNotes = ?, ProcessedAt = ?, ProcessedBy = ?
            WHERE Id = ?
        """, (
            status,
            notes,
            datetime.utcnow().isoformat(),
            request.session.get('user_email'),
            id
        ))
        
        # If approved, update the shift assignment
        if status == 'Genehmigt' and requesting_employee_id:
            cursor.execute("""
                UPDATE ShiftAssignments
                SET EmployeeId = ?, ModifiedAt = ?, ModifiedBy = ?
                WHERE Id = ?
            """, (
                requesting_employee_id,
                datetime.utcnow().isoformat(),
                request.session.get('user_email'),
                shift_assignment_id
            ))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Process shift exchange error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Bearbeiten: {str(e)}'}, status_code=500)
