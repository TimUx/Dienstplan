"""Absence records API routes."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .shared import (
    get_db,
    require_role,
    log_audit,
    get_absence_type_defaults,
    check_csrf,
    parse_json_body,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/absences')
def get_absences(request: Request):
    """Get all absences with their type information"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.*, e.Vorname, e.Name, e.TeamId,
               at.Name as TypeName, at.Code as TypeCode, at.ColorCode as TypeColor
        FROM Absences a
        JOIN Employees e ON a.EmployeeId = e.Id
        LEFT JOIN AbsenceTypes at ON a.AbsenceTypeId = at.Id
        ORDER BY a.StartDate DESC
    """)
    
    absences = []
    for row in cursor.fetchall():
        # Use new type system if available, otherwise fall back to legacy
        if row['TypeName']:
            type_name = row['TypeName']
            type_code = row['TypeCode']
            type_color = row['TypeColor']
        else:
            # Legacy fallback: Map type: 1=AU (Krank), 2=U (Urlaub), 3=L (Lehrgang)
            defaults = get_absence_type_defaults()
            default = defaults.get(row['Type'], {'name': 'Unbekannt', 'code': 'U', 'colorCode': '#E0E0E0'})
            type_name = default['name']
            type_code = default['code']
            type_color = default['colorCode']
        
        absences.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'type': type_name,
            'typeCode': type_code,
            'typeColor': type_color,
            'absenceTypeId': row['AbsenceTypeId'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'notes': row['Notes'],
            'createdAt': row['CreatedAt']
        })
    
    conn.close()
    return absences


@router.post('/api/absences', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_absence(request: Request, data: dict = Depends(parse_json_body)):
    """Create new absence with support for custom absence types"""
    try:
        # Support both legacy 'type' and new 'absenceTypeId'
        absence_type_id = data.get('absenceTypeId')
        legacy_type = data.get('type')
        
        if not data.get('employeeId') or not data.get('startDate') or not data.get('endDate'):
            return JSONResponse(content={'error': 'EmployeeId, StartDate und EndDate sind erforderlich'}, status_code=400)
        
        if not absence_type_id and not legacy_type:
            return JSONResponse(content={'error': 'AbsenceTypeId oder Type ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # If absenceTypeId is provided, use it; otherwise map legacy type to absenceTypeId
        if absence_type_id:
            # Verify absence type exists
            cursor.execute("SELECT Id, Code FROM AbsenceTypes WHERE Id = ?", (absence_type_id,))
            type_row = cursor.fetchone()
            if not type_row:
                conn.close()
                return JSONResponse(content={'error': 'Ungültiger Abwesenheitstyp'}, status_code=400)
            
            # Determine legacy type from code for backward compatibility
            type_code = type_row['Code']
            legacy_type_map = {'AU': 1, 'U': 2, 'L': 3}
            legacy_type_value = legacy_type_map.get(type_code, 1)  # Default to 1 (AU) for custom types
        else:
            # Map legacy type to absenceTypeId
            legacy_to_code = {1: 'AU', 2: 'U', 3: 'L'}
            type_code = legacy_to_code.get(legacy_type, 'U')
            cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ? AND IsSystemType = 1", (type_code,))
            type_row = cursor.fetchone()
            if type_row:
                absence_type_id = type_row['Id']
            legacy_type_value = legacy_type
        
        cursor.execute("""
            INSERT INTO Absences 
            (EmployeeId, Type, AbsenceTypeId, StartDate, EndDate, Notes, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('employeeId'),
            legacy_type_value,
            absence_type_id,
            data.get('startDate'),
            data.get('endDate'),
            data.get('notes'),
            datetime.utcnow().isoformat(),
            request.session.get('user_email')
        ))
        
        absence_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'employeeId': data.get('employeeId'),
            'absenceTypeId': absence_type_id,
            'type': legacy_type_value,
            'startDate': data.get('startDate'),
            'endDate': data.get('endDate'),
            'notes': data.get('notes')
        }, ensure_ascii=False)
        log_audit(conn, 'Absence', absence_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        # Check for understaffing and create notifications
        try:
            from datetime import date
            start_date_obj = date.fromisoformat(data.get('startDate'))
            end_date_obj = date.fromisoformat(data.get('endDate'))
            
            from notification_manager import process_absence_for_notifications
            notification_ids = process_absence_for_notifications(
                conn,
                absence_id,
                data.get('employeeId'),
                start_date_obj,
                end_date_obj,
                data.get('type'),
                request.session.get('user_email')
            )
            
            if notification_ids:
                logger.info(f"Created {len(notification_ids)} understaffing notifications for absence {absence_id}")
            
            # Automatically assign replacements for affected shifts
            from springer_replacement import process_absence_with_springer_assignment
            replacement_results = process_absence_with_springer_assignment(
                conn,
                absence_id,
                data.get('employeeId'),
                start_date_obj,
                end_date_obj,
                data.get('type'),
                request.session.get('user_email')
            )
            
            # Log shift removal and replacement assignments
            shifts_removed = replacement_results.get('shiftsRemoved', 0)
            if shifts_removed > 0:
                logger.info(
                    f"Removed {shifts_removed} shift assignment(s) for absent employee (Absence ID: {absence_id})"
                )
            
            if replacement_results['assignmentsCreated'] > 0:
                logger.info(
                    f"Automatically assigned {replacement_results['assignmentsCreated']} replacements "
                    f"for {replacement_results['shiftsNeedingCoverage']} affected shifts (Absence ID: {absence_id})"
                )
                
                # Include replacement results in response
                conn.commit()
                conn.close()
                
                return JSONResponse(content={
                    'success': True,
                    'id': absence_id,
                    'replacementAssignments': {
                        'assignmentsCreated': replacement_results['assignmentsCreated'],
                        'notificationsSent': replacement_results['notificationsSent'],
                        'shiftsNeedingCoverage': replacement_results['shiftsNeedingCoverage'],
                        'shiftsRemoved': shifts_removed,
                        'details': replacement_results['details']
                    }
                }, status_code=201)
                
        except Exception as notif_error:
            # Log notification error but don't fail the absence creation
            logger.error(f"Error processing absence notifications/replacements: {notif_error}")
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': absence_id}, status_code=201)
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Erstellen der Abwesenheit',
            status_code=500,
            exc=e,
            context='create_absence failed',
        )


@router.delete('/api/absences/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_absence(request: Request, id: int):
    """Delete an absence"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get absence info for audit before deleting
        cursor.execute("""
            SELECT EmployeeId, Type, StartDate, EndDate 
            FROM Absences WHERE Id = ?
        """, (id,))
        absence_row = cursor.fetchone()
        
        if not absence_row:
            conn.close()
            return JSONResponse(content={'error': 'Abwesenheit nicht gefunden'}, status_code=404)
        
        cursor.execute("DELETE FROM Absences WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({
            'employeeId': absence_row['EmployeeId'],
            'type': absence_row['Type'],
            'startDate': absence_row['StartDate'],
            'endDate': absence_row['EndDate']
        }, ensure_ascii=False)
        log_audit(conn, 'Absence', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Löschen der Abwesenheit',
            status_code=500,
            exc=e,
            context='delete_absence failed',
        )

