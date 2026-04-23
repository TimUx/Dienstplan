"""Shift assignment CRUD and bulk update API routes."""

import json
import logging
from datetime import date, datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.put('/api/shifts/assignments/{id:int}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def update_shift_assignment(request: Request, id, data: dict = Depends(parse_json_body)):
    """Update a shift assignment (manual edit)"""
    try:
        
        # Validate data types
        try:
            employee_id = int(data.get('employeeId'))
            shift_type_id = int(data.get('shiftTypeId'))
            assignment_date = date.fromisoformat(data.get('date'))
        except (ValueError, TypeError) as e:
            return JSONResponse(content={'error': f'Ungültige Daten: {str(e)}'}, status_code=400)
        
        conn = None
        try:
            db = get_db()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if assignment exists and get old values for audit
            cursor.execute("""
                SELECT EmployeeId, ShiftTypeId, Date, IsFixed, Notes 
                FROM ShiftAssignments WHERE Id = ?
            """, (id,))
            old_row = cursor.fetchone()
            if not old_row:
                return JSONResponse(content={'error': 'Schichtzuweisung nicht gefunden'}, status_code=404)
            
            # Update assignment
            cursor.execute("""
                UPDATE ShiftAssignments 
                SET EmployeeId = ?, ShiftTypeId = ?, Date = ?, 
                    IsManual = 1, IsFixed = ?, Notes = ?,
                    ModifiedAt = ?, ModifiedBy = ?
                WHERE Id = ?
            """, (
                employee_id,
                shift_type_id,
                assignment_date.isoformat(),
                1 if data.get('isFixed') else 0,
                data.get('notes'),
                datetime.utcnow().isoformat(),
                request.session.get('user_email'),
                id
            ))
            
            # Log audit entry with changes
            changes_dict = {}
            if old_row['EmployeeId'] != employee_id:
                changes_dict['employeeId'] = {'old': old_row['EmployeeId'], 'new': employee_id}
            if old_row['ShiftTypeId'] != shift_type_id:
                changes_dict['shiftTypeId'] = {'old': old_row['ShiftTypeId'], 'new': shift_type_id}
            if old_row['Date'] != assignment_date.isoformat():
                changes_dict['date'] = {'old': old_row['Date'], 'new': assignment_date.isoformat()}
            new_is_fixed = 1 if data.get('isFixed') else 0
            if old_row['IsFixed'] != new_is_fixed:
                changes_dict['isFixed'] = {'old': bool(old_row['IsFixed']), 'new': bool(new_is_fixed)}
            if old_row['Notes'] != data.get('notes'):
                changes_dict['notes'] = {'old': old_row['Notes'], 'new': data.get('notes')}
            
            if changes_dict:
                changes = json.dumps(changes_dict, ensure_ascii=False)
                log_audit(conn, 'ShiftAssignment', id, 'Updated', changes)
            
            conn.commit()
            
            return {'success': True}
            
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Update shift assignment error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.post('/api/shifts/assignments', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def create_shift_assignment(request: Request, data: dict = Depends(parse_json_body)):
    """Create a shift assignment manually"""
    try:
        
        # Validate required fields
        if not data.get('employeeId') or not data.get('shiftTypeId') or not data.get('date'):
            return JSONResponse(content={'error': 'EmployeeId, ShiftTypeId und Date sind erforderlich'}, status_code=400)
        
        # Validate data types
        try:
            employee_id = int(data.get('employeeId'))
            shift_type_id = int(data.get('shiftTypeId'))
            assignment_date = date.fromisoformat(data.get('date'))
        except (ValueError, TypeError) as e:
            return JSONResponse(content={'error': f'Ungültige Daten: {str(e)}'}, status_code=400)
        
        conn = None
        try:
            db = get_db()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check for existing assignment (same employee, date, shift type)
            cursor.execute("""
                SELECT Id FROM ShiftAssignments 
                WHERE EmployeeId = ? AND Date = ? AND ShiftTypeId = ?
            """, (employee_id, assignment_date.isoformat(), shift_type_id))
            
            if cursor.fetchone():
                return JSONResponse(content={'error': 'Diese Schichtzuweisung existiert bereits'}, status_code=400)
            
            # Create assignment
            cursor.execute("""
                INSERT INTO ShiftAssignments 
                (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, Notes, CreatedAt, CreatedBy)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """, (
                employee_id,
                shift_type_id,
                assignment_date.isoformat(),
                1 if data.get('isFixed') else 0,
                data.get('notes'),
                datetime.utcnow().isoformat(),
                request.session.get('user_email')
            ))
            
            assignment_id = cursor.lastrowid
            
            # Log audit entry
            changes = json.dumps({
                'employeeId': employee_id,
                'shiftTypeId': shift_type_id,
                'date': assignment_date.isoformat(),
                'isFixed': data.get('isFixed'),
                'notes': data.get('notes')
            }, ensure_ascii=False)
            log_audit(conn, 'ShiftAssignment', assignment_id, 'Created', changes)
            
            conn.commit()
            
            return JSONResponse(content={'success': True, 'id': assignment_id}, status_code=201)
            
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Create shift assignment error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.delete('/api/shifts/assignments/{id:int}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def delete_shift_assignment(request: Request, id):
    """Delete a shift assignment"""
    try:
        conn = None
        try:
            db = get_db()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if assignment exists and get info for audit
            cursor.execute("""
                SELECT EmployeeId, ShiftTypeId, Date, IsFixed 
                FROM ShiftAssignments WHERE Id = ?
            """, (id,))
            row = cursor.fetchone()
            
            if not row:
                return JSONResponse(content={'error': 'Schichtzuweisung nicht gefunden'}, status_code=404)
            
            # Warn if trying to delete a fixed assignment
            if row['IsFixed']:
                return JSONResponse(content={'error': 'Fixierte Schichtzuweisungen können nicht gelöscht werden. Bitte erst entsperren.'}, status_code=400)
            
            # Delete assignment
            cursor.execute("DELETE FROM ShiftAssignments WHERE Id = ?", (id,))
            
            # Log audit entry
            changes = json.dumps({
                'employeeId': row['EmployeeId'],
                'shiftTypeId': row['ShiftTypeId'],
                'date': row['Date']
            }, ensure_ascii=False)
            log_audit(conn, 'ShiftAssignment', id, 'Deleted', changes)
            
            conn.commit()
            
            return {'success': True}
            
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Delete shift assignment error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


@router.put('/api/shifts/assignments/bulk', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def bulk_update_shift_assignments(request: Request, data: dict = Depends(parse_json_body)):
    """Bulk update multiple shift assignments"""
    try:
        
        # Validate required fields
        if not data.get('shiftIds') or not isinstance(data.get('shiftIds'), list):
            return JSONResponse(content={'error': 'ShiftIds array ist erforderlich'}, status_code=400)
        
        if not data.get('changes') or not isinstance(data.get('changes'), dict):
            return JSONResponse(content={'error': 'Changes object ist erforderlich'}, status_code=400)
        
        shift_ids = data['shiftIds']
        changes = data['changes']
        
        if len(shift_ids) == 0:
            return JSONResponse(content={'error': 'Keine Schichten zum Aktualisieren ausgewählt'}, status_code=400)
        
        # Validate that at least one field is being changed
        allowed_fields = {'employeeId', 'shiftTypeId', 'isFixed', 'notes'}
        if not any(key in changes for key in allowed_fields):
            return JSONResponse(content={'error': 'Mindestens ein Feld muss geändert werden'}, status_code=400)
        
        # Validate that only allowed fields are present
        invalid_fields = set(changes.keys()) - allowed_fields
        if invalid_fields:
            return JSONResponse(content={'error': f'Ungültige Felder: {", ".join(invalid_fields)}'}, status_code=400)
        
        conn = None
        updated_count = 0
        try:
            db = get_db()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Whitelist for allowed column names to prevent SQL injection
            ALLOWED_COLUMNS = {
                'employeeId': 'EmployeeId',
                'shiftTypeId': 'ShiftTypeId',
                'isFixed': 'IsFixed',
                'notes': 'Notes'
            }
            
            # Process each shift
            for shift_id in shift_ids:
                # Verify shift exists
                cursor.execute("SELECT Id FROM ShiftAssignments WHERE Id = ?", (shift_id,))
                if not cursor.fetchone():
                    logger.warning(f"Shift {shift_id} not found, skipping")
                    continue
                
                # Build UPDATE query dynamically based on changes
                update_fields = []
                update_values = []
                
                if 'employeeId' in changes:
                    update_fields.append(f"{ALLOWED_COLUMNS['employeeId']} = ?")
                    update_values.append(changes['employeeId'])
                
                if 'shiftTypeId' in changes:
                    update_fields.append(f"{ALLOWED_COLUMNS['shiftTypeId']} = ?")
                    update_values.append(changes['shiftTypeId'])
                
                if 'isFixed' in changes:
                    update_fields.append(f"{ALLOWED_COLUMNS['isFixed']} = ?")
                    update_values.append(1 if changes['isFixed'] else 0)
                
                if 'notes' in changes:
                    # Append notes instead of replacing
                    cursor.execute("SELECT Notes FROM ShiftAssignments WHERE Id = ?", (shift_id,))
                    row = cursor.fetchone()
                    existing_notes = row['Notes'] if row and row['Notes'] else ''
                    new_notes = existing_notes
                    if existing_notes:
                        new_notes += '\n' + changes['notes']
                    else:
                        new_notes = changes['notes']
                    update_fields.append(f"{ALLOWED_COLUMNS['notes']} = ?")
                    update_values.append(new_notes)
                
                # Always update modification timestamp and user
                update_fields.append("ModifiedAt = ?")
                update_fields.append("ModifiedBy = ?")
                update_values.append(datetime.utcnow().isoformat())
                update_values.append(request.session.get('user_email'))
                
                # Add shift ID as last parameter
                update_values.append(shift_id)
                
                # Execute update - fields are from whitelist, safe to use in f-string
                update_query = f"""
                    UPDATE ShiftAssignments 
                    SET {', '.join(update_fields)}
                    WHERE Id = ?
                """
                
                cursor.execute(update_query, update_values)
                
                # Log audit entry
                changes_json = json.dumps(changes, ensure_ascii=False)
                log_audit(conn, 'ShiftAssignment', shift_id, 'BulkUpdate', changes_json)
                
                updated_count += 1
            
            conn.commit()
            
            return {
                'success': True,
                'updated': updated_count,
                'total': len(shift_ids)
            }
            
        finally:
            if conn:
                conn.close()
        
    except ValueError as e:
        logger.error(f"Bulk update validation error: {str(e)}")
        return JSONResponse(content={'error': f'Validierungsfehler: {str(e)}'}, status_code=400)
    except Exception as e:
        logger.error(f"Bulk update shift assignments error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.put('/api/shifts/assignments/{id:int}/toggle-fixed', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def toggle_fixed_assignment(request: Request, id):
    """Toggle the IsFixed flag on an assignment (lock/unlock)"""
    try:
        conn = None
        try:
            db = get_db()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if assignment exists
            cursor.execute("SELECT Id, IsFixed FROM ShiftAssignments WHERE Id = ?", (id,))
            row = cursor.fetchone()
            
            if not row:
                return JSONResponse(content={'error': 'Schichtzuweisung nicht gefunden'}, status_code=404)
            
            # Toggle fixed status
            new_fixed_status = 0 if row['IsFixed'] else 1
            
            cursor.execute("""
                UPDATE ShiftAssignments 
                SET IsFixed = ?, ModifiedAt = ?, ModifiedBy = ?
                WHERE Id = ?
            """, (
                new_fixed_status,
                datetime.utcnow().isoformat(),
                request.session.get('user_email'),
                id
            ))
            
            conn.commit()
            
            return {
                'success': True,
                'isFixed': bool(new_fixed_status)
            }
            
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Toggle fixed assignment error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Sperren/Entsperren: {str(e)}'}, status_code=500)

