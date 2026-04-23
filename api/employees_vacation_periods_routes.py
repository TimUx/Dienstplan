"""Vacation periods (Ferienzeiten) API routes."""

import json
import logging
from datetime import date, datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/vacation-periods')
def get_vacation_periods(request: Request):
    """Get all vacation periods"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, StartDate, EndDate, ColorCode, 
                   CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM VacationPeriods
            ORDER BY StartDate
        """)
        
        periods = []
        for row in cursor.fetchall():
            periods.append({
                'id': row['Id'],
                'name': row['Name'],
                'startDate': row['StartDate'],
                'endDate': row['EndDate'],
                'colorCode': row['ColorCode'] or '#E8F5E9',
                'createdAt': row['CreatedAt'],
                'createdBy': row['CreatedBy'],
                'modifiedAt': row['ModifiedAt'],
                'modifiedBy': row['ModifiedBy']
            })
        
        conn.close()
        return periods
        
    except Exception as e:
        logger.error(f"Get vacation periods error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.get('/api/vacation-periods/{id}')
def get_vacation_period(request: Request, id: int):
    """Get a specific vacation period"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, StartDate, EndDate, ColorCode, 
                   CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM VacationPeriods
            WHERE Id = ?
        """, (id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return JSONResponse(content={'error': 'Ferienzeit nicht gefunden'}, status_code=404)
        
        return {
            'id': row['Id'],
            'name': row['Name'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'colorCode': row['ColorCode'] or '#E8F5E9',
            'createdAt': row['CreatedAt'],
            'createdBy': row['CreatedBy'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        }
        
    except Exception as e:
        logger.error(f"Get vacation period error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.post('/api/vacation-periods', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_vacation_period(request: Request, data: dict = Depends(parse_json_body)):
    """Create new vacation period"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Name ist Pflichtfeld'}, status_code=400)
        if not data.get('startDate'):
            return JSONResponse(content={'error': 'Startdatum ist Pflichtfeld'}, status_code=400)
        if not data.get('endDate'):
            return JSONResponse(content={'error': 'Enddatum ist Pflichtfeld'}, status_code=400)
        
        # Validate dates
        try:
            start_date = date.fromisoformat(data.get('startDate'))
            end_date = date.fromisoformat(data.get('endDate'))
        except (ValueError, TypeError):
            return JSONResponse(content={'error': 'Ungültiges Datumsformat'}, status_code=400)
        
        if end_date < start_date:
            return JSONResponse(content={'error': 'Enddatum muss nach Startdatum liegen'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO VacationPeriods (Name, StartDate, EndDate, ColorCode, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('name'),
            start_date.isoformat(),
            end_date.isoformat(),
            data.get('colorCode', '#E8F5E9'),
            datetime.utcnow().isoformat(),
            request.session.get('user_email')
        ))
        
        period_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'colorCode': data.get('colorCode', '#E8F5E9')
        }, ensure_ascii=False)
        log_audit(conn, 'VacationPeriod', period_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': period_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create vacation period error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/vacation-periods/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_vacation_period(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update vacation period"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Name ist Pflichtfeld'}, status_code=400)
        if not data.get('startDate'):
            return JSONResponse(content={'error': 'Startdatum ist Pflichtfeld'}, status_code=400)
        if not data.get('endDate'):
            return JSONResponse(content={'error': 'Enddatum ist Pflichtfeld'}, status_code=400)
        
        # Validate dates
        try:
            start_date = date.fromisoformat(data.get('startDate'))
            end_date = date.fromisoformat(data.get('endDate'))
        except (ValueError, TypeError):
            return JSONResponse(content={'error': 'Ungültiges Datumsformat'}, status_code=400)
        
        if end_date < start_date:
            return JSONResponse(content={'error': 'Enddatum muss nach Startdatum liegen'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if period exists and get old values for audit
        cursor.execute("""
            SELECT Name, StartDate, EndDate, ColorCode 
            FROM VacationPeriods WHERE Id = ?
        """, (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Ferienzeit nicht gefunden'}, status_code=404)
        
        cursor.execute("""
            UPDATE VacationPeriods 
            SET Name = ?, StartDate = ?, EndDate = ?, ColorCode = ?,
                ModifiedAt = ?, ModifiedBy = ?
            WHERE Id = ?
        """, (
            data.get('name'),
            start_date.isoformat(),
            end_date.isoformat(),
            data.get('colorCode', '#E8F5E9'),
            datetime.utcnow().isoformat(),
            request.session.get('user_email'),
            id
        ))
        
        # Log audit entry with changes
        changes_dict = {}
        if old_row['Name'] != data.get('name'):
            changes_dict['name'] = {'old': old_row['Name'], 'new': data.get('name')}
        if old_row['StartDate'] != start_date.isoformat():
            changes_dict['startDate'] = {'old': old_row['StartDate'], 'new': start_date.isoformat()}
        if old_row['EndDate'] != end_date.isoformat():
            changes_dict['endDate'] = {'old': old_row['EndDate'], 'new': end_date.isoformat()}
        if old_row['ColorCode'] != data.get('colorCode', '#E8F5E9'):
            changes_dict['colorCode'] = {'old': old_row['ColorCode'], 'new': data.get('colorCode', '#E8F5E9')}
        
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'VacationPeriod', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update vacation period error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/vacation-periods/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_vacation_period(request: Request, id: int):
    """Delete vacation period (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if period exists and get info for audit
        cursor.execute("SELECT Name FROM VacationPeriods WHERE Id = ?", (id,))
        period_row = cursor.fetchone()
        if not period_row:
            conn.close()
            return JSONResponse(content={'error': 'Ferienzeit nicht gefunden'}, status_code=404)
        
        # Delete period
        cursor.execute("DELETE FROM VacationPeriods WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'name': period_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'VacationPeriod', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete vacation period error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)

