"""
Absences Blueprint: absences, absence types, vacation requests, vacation year approvals/plan.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
import json
import logging

from .shared import get_db, require_auth, require_role, log_audit, require_csrf, get_absence_type_defaults, check_csrf, parse_json_body

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
        logger.error(f"Create absence error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


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
        logger.error(f"Delete absence error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# ============================================================================
# ABSENCE TYPE ENDPOINTS
# ============================================================================

@router.get('/api/absencetypes')
def get_absence_types(request: Request):
    """Get all absence types (system and custom)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Id, Name, Code, ColorCode, IsSystemType, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
        FROM AbsenceTypes
        ORDER BY IsSystemType DESC, Name ASC
    """)
    
    absence_types = []
    for row in cursor.fetchall():
        absence_types.append({
            'id': row['Id'],
            'name': row['Name'],
            'code': row['Code'],
            'colorCode': row['ColorCode'],
            'isSystemType': bool(row['IsSystemType']),
            'createdAt': row['CreatedAt'],
            'createdBy': row['CreatedBy'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        })
    
    conn.close()
    return absence_types


@router.post('/api/absencetypes', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_absence_type(request: Request, data: dict = Depends(parse_json_body)):
    """Create new custom absence type (Admin only)"""
    try:
        if not data.get('name') or not data.get('code'):
            return JSONResponse(content={'error': 'Name und Code sind erforderlich'}, status_code=400)
        
        # Validate code doesn't conflict with system types
        code = data.get('code').upper()
        if code in ['U', 'AU', 'L']:
            return JSONResponse(content={'error': 'Code U, AU und L sind für Systemtypen reserviert'}, status_code=400)
        
        # Set default color if not provided
        color_code = data.get('colorCode', '#E0E0E0')
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if code already exists
        cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ?", (code,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': f'Ein Abwesenheitstyp mit dem Kürzel "{code}" existiert bereits'}, status_code=400)
        
        cursor.execute("""
            INSERT INTO AbsenceTypes 
            (Name, Code, ColorCode, IsSystemType, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (
            data.get('name'),
            code,
            color_code,
            datetime.utcnow().isoformat(),
            request.session.get('user_email')
        ))
        
        absence_type_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'code': code,
            'colorCode': color_code
        }, ensure_ascii=False)
        log_audit(conn, 'AbsenceType', absence_type_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': absence_type_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/absencetypes/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_absence_type(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update custom absence type (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if absence type exists and is not a system type
        cursor.execute("SELECT IsSystemType, Code FROM AbsenceTypes WHERE Id = ?", (id,))
        type_row = cursor.fetchone()
        
        if not type_row:
            conn.close()
            return JSONResponse(content={'error': 'Abwesenheitstyp nicht gefunden'}, status_code=404)
        
        if type_row['IsSystemType']:
            conn.close()
            return JSONResponse(content={'error': 'Systemtypen (U, AU, L) können nicht geändert werden'}, status_code=400)
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = []
        
        if data.get('name'):
            update_fields.append("Name = ?")
            params.append(data.get('name'))
        
        if data.get('code'):
            new_code = data.get('code').upper()
            if new_code in ['U', 'AU', 'L']:
                conn.close()
                return JSONResponse(content={'error': 'Code U, AU und L sind für Systemtypen reserviert'}, status_code=400)
            
            # Check if code already exists for a different type
            cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ? AND Id != ?", (new_code, id))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': f'Ein Abwesenheitstyp mit dem Kürzel "{new_code}" existiert bereits'}, status_code=400)
            
            update_fields.append("Code = ?")
            params.append(new_code)
        
        if data.get('colorCode'):
            update_fields.append("ColorCode = ?")
            params.append(data.get('colorCode'))
        
        if not update_fields:
            conn.close()
            return JSONResponse(content={'error': 'Keine Felder zum Aktualisieren'}, status_code=400)
        
        update_fields.append("ModifiedAt = ?")
        params.append(datetime.utcnow().isoformat())
        
        update_fields.append("ModifiedBy = ?")
        params.append(request.session.get('user_email'))
        
        params.append(id)
        
        cursor.execute(f"""
            UPDATE AbsenceTypes 
            SET {', '.join(update_fields)}
            WHERE Id = ?
        """, params)
        
        # Log audit entry
        log_audit(conn, 'AbsenceType', id, 'Updated', json.dumps(data, ensure_ascii=False), user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/absencetypes/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_absence_type(request: Request, id: int):
    """Delete custom absence type (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if absence type exists and is not a system type
        cursor.execute("SELECT IsSystemType, Code, Name FROM AbsenceTypes WHERE Id = ?", (id,))
        type_row = cursor.fetchone()
        
        if not type_row:
            conn.close()
            return JSONResponse(content={'error': 'Abwesenheitstyp nicht gefunden'}, status_code=404)
        
        if type_row['IsSystemType']:
            conn.close()
            return JSONResponse(content={'error': 'Systemtypen (U, AU, L) können nicht gelöscht werden'}, status_code=400)
        
        # Check if any absences use this type
        cursor.execute("SELECT COUNT(*) FROM Absences WHERE AbsenceTypeId = ?", (id,))
        usage_count = cursor.fetchone()[0]
        
        if usage_count > 0:
            conn.close()
            return JSONResponse(content={
                'error': f'Dieser Abwesenheitstyp kann nicht gelöscht werden, da er von {usage_count} Abwesenheit(en) verwendet wird'
            }, status_code=400)
        
        cursor.execute("DELETE FROM AbsenceTypes WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({
            'code': type_row['Code'],
            'name': type_row['Name']
        }, ensure_ascii=False)
        log_audit(conn, 'AbsenceType', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# ============================================================================
# VACATION REQUEST ENDPOINTS
# ============================================================================

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


# ============================================================================
# VACATION YEAR APPROVAL ENDPOINTS
# ============================================================================

@router.get('/api/vacationyearapprovals')
def get_vacation_year_approvals(request: Request):
    """Get all vacation year approvals"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM VacationYearApprovals
        ORDER BY Year DESC
    """)
    
    approvals = []
    for row in cursor.fetchall():
        approvals.append({
            'id': row['Id'],
            'year': row['Year'],
            'isApproved': bool(row['IsApproved']),
            'approvedAt': row['ApprovedAt'],
            'approvedBy': row['ApprovedBy'],
            'createdAt': row['CreatedAt'],
            'modifiedAt': row['ModifiedAt'],
            'notes': row['Notes']
        })
    
    conn.close()
    return approvals


@router.get('/api/vacationyearapprovals/{year}')
def get_vacation_year_approval(request: Request, year: int):
    """Get vacation year approval status for a specific year"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM VacationYearApprovals WHERE Year = ?
    """, (year,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {
            'year': year,
            'isApproved': False,
            'exists': False
        }
    
    return {
        'id': row['Id'],
        'year': row['Year'],
        'isApproved': bool(row['IsApproved']),
        'approvedAt': row['ApprovedAt'],
        'approvedBy': row['ApprovedBy'],
        'createdAt': row['CreatedAt'],
        'modifiedAt': row['ModifiedAt'],
        'notes': row['Notes'],
        'exists': True
    }


@router.post('/api/vacationyearapprovals', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_or_update_vacation_year_approval(request: Request, data: dict = Depends(parse_json_body)):
    """Create or update vacation year approval (Admin only)"""
    try:
        year = data.get('year')
        is_approved = data.get('isApproved', False)
        notes = data.get('notes')
        
        if not year:
            return JSONResponse(content={'error': 'Jahr ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if entry exists
        cursor.execute("""
            SELECT Id FROM VacationYearApprovals WHERE Year = ?
        """, (year,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute("""
                UPDATE VacationYearApprovals 
                SET IsApproved = ?,
                    ApprovedAt = ?,
                    ApprovedBy = ?,
                    ModifiedAt = ?,
                    Notes = ?
                WHERE Year = ?
            """, (
                1 if is_approved else 0,
                datetime.utcnow().isoformat() if is_approved else None,
                request.session.get('user_email') if is_approved else None,
                datetime.utcnow().isoformat(),
                notes,
                year
            ))
            
            approval_id = existing['Id']
            action = 'Updated'
        else:
            # Create new entry
            cursor.execute("""
                INSERT INTO VacationYearApprovals 
                (Year, IsApproved, ApprovedAt, ApprovedBy, CreatedAt, Notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                year,
                1 if is_approved else 0,
                datetime.utcnow().isoformat() if is_approved else None,
                request.session.get('user_email') if is_approved else None,
                datetime.utcnow().isoformat(),
                notes
            ))
            
            approval_id = cursor.lastrowid
            action = 'Created'
        
        # Log audit entry
        changes = json.dumps({
            'year': year,
            'isApproved': is_approved,
            'notes': notes
        }, ensure_ascii=False)
        log_audit(conn, 'VacationYearApproval', approval_id, action, changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': approval_id, 'year': year}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create/update vacation year approval error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Speichern: {str(e)}'}, status_code=500)


@router.get('/api/vacationyearplan/{year}')
def get_vacation_year_plan(request: Request, year: int):
    """
    Get vacation plan for a specific year.
    Returns vacation data only if the year is approved by admin.
    All users can access this endpoint.
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if year is approved
    cursor.execute("""
        SELECT IsApproved FROM VacationYearApprovals WHERE Year = ?
    """, (year,))
    
    approval_row = cursor.fetchone()
    
    # If year is not approved, return empty data
    if not approval_row or not approval_row['IsApproved']:
        conn.close()
        return {
            'year': year,
            'isApproved': False,
            'vacations': [],
            'message': 'Urlaubsdaten für dieses Jahr wurden noch nicht freigegeben.'
        }
    
    # Get all vacation data for the year (from VacationRequests and Absences)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get approved vacation requests
    cursor.execute("""
        SELECT 
            vr.Id,
            vr.EmployeeId,
            e.Vorname,
            e.Name,
            e.TeamId,
            t.Name as TeamName,
            vr.StartDate,
            vr.EndDate,
            vr.Status,
            vr.Notes,
            'VacationRequest' as Source
        FROM VacationRequests vr
        JOIN Employees e ON vr.EmployeeId = e.Id
        LEFT JOIN Teams t ON e.TeamId = t.Id
        WHERE (vr.StartDate <= ? AND vr.EndDate >= ?)
        ORDER BY vr.StartDate, e.Name, e.Vorname
    """, (end_date, start_date))
    
    vacation_requests = []
    for row in cursor.fetchall():
        vacation_requests.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': row['Status'],
            'notes': row['Notes'],
            'source': row['Source']
        })
    
    # Get vacation absences (Type 2 = Urlaub)
    cursor.execute("""
        SELECT 
            a.Id,
            a.EmployeeId,
            e.Vorname,
            e.Name,
            e.TeamId,
            t.Name as TeamName,
            a.StartDate,
            a.EndDate,
            a.Notes,
            'Absence' as Source
        FROM Absences a
        JOIN Employees e ON a.EmployeeId = e.Id
        LEFT JOIN Teams t ON e.TeamId = t.Id
        WHERE a.Type = 2
        AND (a.StartDate <= ? AND a.EndDate >= ?)
        ORDER BY a.StartDate, e.Name, e.Vorname
    """, (end_date, start_date))
    
    absences = []
    for row in cursor.fetchall():
        absences.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': 'Genehmigt',  # Absences are always approved
            'notes': row['Notes'],
            'source': row['Source']
        })
    
    conn.close()
    
    return {
        'year': year,
        'isApproved': True,
        'vacationRequests': vacation_requests,
        'absences': absences
    }
