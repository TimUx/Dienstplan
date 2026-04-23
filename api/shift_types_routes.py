"""Shift types and team–shift-type assignment API routes."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, get_row_value, check_csrf, parse_json_body
from .repositories.shift_repository import ShiftRepository

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/shifttypes')
def get_shift_types(request: Request):
    """Get all shift types"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    shift_types = []
    for row in ShiftRepository.get_all_shift_types(cursor):
        # Handle MaxConsecutiveDays for backward compatibility
        try:
            max_consecutive_days = row['MaxConsecutiveDays']
        except (KeyError, IndexError):
            max_consecutive_days = 6  # Default value
        
        shift_types.append({
            'id': row['Id'],
            'code': row['Code'],
            'name': row['Name'],
            'startTime': row['StartTime'],
            'endTime': row['EndTime'],
            'colorCode': row['ColorCode'],
            'durationHours': row['DurationHours'],
            'weeklyWorkingHours': row['WeeklyWorkingHours'],
            'isActive': bool(row['IsActive']),
            'worksMonday': bool(row['WorksMonday']),
            'worksTuesday': bool(row['WorksTuesday']),
            'worksWednesday': bool(row['WorksWednesday']),
            'worksThursday': bool(row['WorksThursday']),
            'worksFriday': bool(row['WorksFriday']),
            'worksSaturday': bool(row['WorksSaturday']),
            'worksSunday': bool(row['WorksSunday']),
            'minStaffWeekday': row['MinStaffWeekday'],
            'maxStaffWeekday': row['MaxStaffWeekday'],
            'minStaffWeekend': row['MinStaffWeekend'],
            'maxStaffWeekend': row['MaxStaffWeekend'],
            'maxConsecutiveDays': max_consecutive_days
        })
    
    conn.close()
    return shift_types


@router.post('/api/shifttypes', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_shift_type(request: Request, data: dict = Depends(parse_json_body)):
    """Create new shift type (Admin only)"""
    try:
        
        # Validate required fields
        required_fields = ['code', 'name', 'startTime', 'endTime', 'durationHours']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(content={'error': f'{field} ist Pflichtfeld'}, status_code=400)
        
        # Validate staffing requirements
        min_staff_weekday = data.get('minStaffWeekday', 3)
        max_staff_weekday = data.get('maxStaffWeekday', 5)
        min_staff_weekend = data.get('minStaffWeekend', 2)
        max_staff_weekend = data.get('maxStaffWeekend', 3)
        max_consecutive_days = data.get('maxConsecutiveDays', 6)
        
        if min_staff_weekday > max_staff_weekday:
            return JSONResponse(content={'error': 'Minimale Personalstärke an Wochentagen darf nicht größer sein als die maximale Personalstärke'}, status_code=400)
        if min_staff_weekend > max_staff_weekend:
            return JSONResponse(content={'error': 'Minimale Personalstärke am Wochenende darf nicht größer sein als die maximale Personalstärke'}, status_code=400)
        if max_consecutive_days < 1 or max_consecutive_days > 10:
            return JSONResponse(content={'error': 'Maximale aufeinanderfolgende Tage muss zwischen 1 und 10 liegen'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if code already exists
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = ?", (data.get('code'),))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Schichtkürzel bereits vorhanden'}, status_code=400)
        
        # Insert shift type
        cursor.execute("""
            INSERT INTO ShiftTypes (Code, Name, StartTime, EndTime, DurationHours, ColorCode, IsActive,
                                  WorksMonday, WorksTuesday, WorksWednesday, WorksThursday, WorksFriday,
                                  WorksSaturday, WorksSunday, WeeklyWorkingHours, 
                                  MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend, 
                                  MaxConsecutiveDays, CreatedBy)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('code'),
            data.get('name'),
            data.get('startTime'),
            data.get('endTime'),
            data.get('durationHours'),
            data.get('colorCode', '#808080'),
            1 if data.get('worksMonday', True) else 0,
            1 if data.get('worksTuesday', True) else 0,
            1 if data.get('worksWednesday', True) else 0,
            1 if data.get('worksThursday', True) else 0,
            1 if data.get('worksFriday', True) else 0,
            1 if data.get('worksSaturday', False) else 0,
            1 if data.get('worksSunday', False) else 0,
            data.get('weeklyWorkingHours', 40.0),
            min_staff_weekday,
            max_staff_weekday,
            min_staff_weekend,
            max_staff_weekend,
            max_consecutive_days,
            request.session.get('user_email', 'system')
        ))
        
        shift_type_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps(data, ensure_ascii=False)
        log_audit(conn, 'ShiftType', shift_type_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': shift_type_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create shift type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.get('/api/shifttypes/{id:int}')

def get_shift_type(request: Request, id):
    """Get single shift type by ID"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    row = ShiftRepository.get_shift_type_by_id(cursor, id)
    
    if not row:
        conn.close()
        return JSONResponse(content={'error': 'Schichttyp nicht gefunden'}, status_code=404)
    
    shift_type = {
        'id': row['Id'],
        'code': row['Code'],
        'name': row['Name'],
        'startTime': row['StartTime'],
        'endTime': row['EndTime'],
        'durationHours': row['DurationHours'],
        'colorCode': row['ColorCode'],
        'isActive': bool(row['IsActive']),
        'worksMonday': bool(row['WorksMonday']),
        'worksTuesday': bool(row['WorksTuesday']),
        'worksWednesday': bool(row['WorksWednesday']),
        'worksThursday': bool(row['WorksThursday']),
        'worksFriday': bool(row['WorksFriday']),
        'worksSaturday': bool(row['WorksSaturday']),
        'worksSunday': bool(row['WorksSunday']),
        'weeklyWorkingHours': row['WeeklyWorkingHours'],
        'minStaffWeekday': row['MinStaffWeekday'],
        'maxStaffWeekday': row['MaxStaffWeekday'],
        'minStaffWeekend': row['MinStaffWeekend'],
        'maxStaffWeekend': row['MaxStaffWeekend']
    }
    
    # Handle MaxConsecutiveDays for backward compatibility
    try:
        shift_type['maxConsecutiveDays'] = row['MaxConsecutiveDays']
    except (KeyError, IndexError):
        shift_type['maxConsecutiveDays'] = 6  # Default value
    
    conn.close()
    return shift_type


@router.put('/api/shifttypes/{id:int}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def update_shift_type(request: Request, id, data: dict = Depends(parse_json_body)):
    """Update shift type (Admin only)"""
    try:
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if shift type exists
        cursor.execute("SELECT * FROM ShiftTypes WHERE Id = ?", (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Schichttyp nicht gefunden'}, status_code=404)
        
        # Check if new code conflicts with existing
        if data.get('code') and data.get('code') != old_row['Code']:
            cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = ? AND Id != ?", 
                         (data.get('code'), id))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': 'Schichtkürzel bereits vorhanden'}, status_code=400)
        
        # Validate staffing requirements using the helper function
        min_staff_weekday = data.get('minStaffWeekday', get_row_value(old_row, 'MinStaffWeekday', 3))
        max_staff_weekday = data.get('maxStaffWeekday', get_row_value(old_row, 'MaxStaffWeekday', 5))
        min_staff_weekend = data.get('minStaffWeekend', get_row_value(old_row, 'MinStaffWeekend', 2))
        max_staff_weekend = data.get('maxStaffWeekend', get_row_value(old_row, 'MaxStaffWeekend', 3))
        max_consecutive_days = data.get('maxConsecutiveDays', get_row_value(old_row, 'MaxConsecutiveDays', 6))
        
        if min_staff_weekday > max_staff_weekday:
            conn.close()
            return JSONResponse(content={'error': 'Minimale Personalstärke an Wochentagen darf nicht größer sein als die maximale Personalstärke'}, status_code=400)
        if min_staff_weekend > max_staff_weekend:
            conn.close()
            return JSONResponse(content={'error': 'Minimale Personalstärke am Wochenende darf nicht größer sein als die maximale Personalstärke'}, status_code=400)
        if max_consecutive_days < 1 or max_consecutive_days > 10:
            conn.close()
            return JSONResponse(content={'error': 'Maximale aufeinanderfolgende Tage muss zwischen 1 und 10 liegen'}, status_code=400)
        
        # Update shift type
        cursor.execute("""
            UPDATE ShiftTypes 
            SET Code = ?, Name = ?, StartTime = ?, EndTime = ?, 
                DurationHours = ?, ColorCode = ?, IsActive = ?,
                WorksMonday = ?, WorksTuesday = ?, WorksWednesday = ?, WorksThursday = ?, WorksFriday = ?,
                WorksSaturday = ?, WorksSunday = ?, WeeklyWorkingHours = ?,
                MinStaffWeekday = ?, MaxStaffWeekday = ?, MinStaffWeekend = ?, MaxStaffWeekend = ?,
                MaxConsecutiveDays = ?, ModifiedAt = ?, ModifiedBy = ?
            WHERE Id = ?
        """, (
            data.get('code', old_row['Code']),
            data.get('name', old_row['Name']),
            data.get('startTime', old_row['StartTime']),
            data.get('endTime', old_row['EndTime']),
            data.get('durationHours', old_row['DurationHours']),
            data.get('colorCode', old_row['ColorCode']),
            1 if data.get('isActive', True) else 0,
            1 if data.get('worksMonday', get_row_value(old_row, 'WorksMonday', True)) else 0,
            1 if data.get('worksTuesday', get_row_value(old_row, 'WorksTuesday', True)) else 0,
            1 if data.get('worksWednesday', get_row_value(old_row, 'WorksWednesday', True)) else 0,
            1 if data.get('worksThursday', get_row_value(old_row, 'WorksThursday', True)) else 0,
            1 if data.get('worksFriday', get_row_value(old_row, 'WorksFriday', True)) else 0,
            1 if data.get('worksSaturday', get_row_value(old_row, 'WorksSaturday', False)) else 0,
            1 if data.get('worksSunday', get_row_value(old_row, 'WorksSunday', False)) else 0,
            data.get('weeklyWorkingHours', get_row_value(old_row, 'WeeklyWorkingHours', 40.0)),
            min_staff_weekday,
            max_staff_weekday,
            min_staff_weekend,
            max_staff_weekend,
            max_consecutive_days,
            datetime.utcnow().isoformat(),
            request.session.get('user_email', 'system'),
            id
        ))
        
        # Log audit entry
        changes_dict = {}
        for field in ['code', 'name', 'startTime', 'endTime', 'durationHours', 'colorCode', 'isActive']:
            db_field = field[0].upper() + field[1:]
            if field == 'isActive':
                db_field = 'IsActive'
            elif field == 'startTime':
                db_field = 'StartTime'
            elif field == 'endTime':
                db_field = 'EndTime'
            elif field == 'durationHours':
                db_field = 'DurationHours'
            elif field == 'colorCode':
                db_field = 'ColorCode'
            else:
                db_field = field[0].upper() + field[1:]
            
            if field in data:
                old_val = old_row[db_field]
                new_val = data[field]
                if field == 'isActive':
                    old_val = bool(old_val)
                if old_val != new_val:
                    changes_dict[field] = {'old': old_val, 'new': new_val}
        
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'ShiftType', id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update shift type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/shifttypes/{id:int}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def delete_shift_type(request: Request, id):
    """Delete shift type (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if shift type exists
        cursor.execute("SELECT Code, Name FROM ShiftTypes WHERE Id = ?", (id,))
        shift_row = cursor.fetchone()
        if not shift_row:
            conn.close()
            return JSONResponse(content={'error': 'Schichttyp nicht gefunden'}, status_code=404)
        
        # Check if shift type is used in assignments
        cursor.execute("SELECT COUNT(*) as count FROM ShiftAssignments WHERE ShiftTypeId = ?", (id,))
        assignment_count = cursor.fetchone()['count']
        
        if assignment_count > 0:
            conn.close()
            return JSONResponse(content={'error': f'Schichttyp wird in {assignment_count} Zuweisungen verwendet und kann nicht gelöscht werden'}, status_code=400)
        
        # Delete shift type (cascade will delete relationships and team assignments)
        cursor.execute("DELETE FROM ShiftTypes WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'code': shift_row['Code'], 'name': shift_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'ShiftType', id, 'Deleted', changes)
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete shift type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# Team-Shift Assignment endpoints
@router.get('/api/shifttypes/{shift_id:int}/teams')

def get_shift_type_teams(request: Request, shift_id):
    """Get teams assigned to a shift type"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.Id, t.Name
        FROM Teams t
        INNER JOIN TeamShiftAssignments tsa ON t.Id = tsa.TeamId
        WHERE tsa.ShiftTypeId = ?
        ORDER BY t.Name
    """, (shift_id,))
    
    teams = []
    for row in cursor.fetchall():
        teams.append({
            'id': row['Id'],
            'name': row['Name']
        })
    
    conn.close()
    return teams


@router.put('/api/shifttypes/{shift_id:int}/teams', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def update_shift_type_teams(request: Request, shift_id, data: dict = Depends(parse_json_body)):
    """Update teams assigned to a shift type (Admin only)"""
    try:
        team_ids = data.get('teamIds', [])
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if shift type exists
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Id = ?", (shift_id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Schichttyp nicht gefunden'}, status_code=404)
        
        # Delete all existing assignments for this shift
        cursor.execute("DELETE FROM TeamShiftAssignments WHERE ShiftTypeId = ?", (shift_id,))
        
        # Insert new assignments
        for team_id in team_ids:
            cursor.execute("""
                INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedBy)
                VALUES (?, ?, ?)
            """, (team_id, shift_id, request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'shiftTypeId': shift_id, 'teamIds': team_ids}, ensure_ascii=False)
        log_audit(conn, 'TeamShiftAssignment', shift_id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update shift type teams error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.get('/api/teams/{team_id:int}/shifttypes')

def get_team_shift_types(request: Request, team_id):
    """Get shift types assigned to a team"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT st.Id, st.Code, st.Name, st.ColorCode
        FROM ShiftTypes st
        INNER JOIN TeamShiftAssignments tsa ON st.Id = tsa.ShiftTypeId
        WHERE tsa.TeamId = ? AND st.IsActive = 1
        ORDER BY st.Code
    """, (team_id,))
    
    shift_types = []
    for row in cursor.fetchall():
        shift_types.append({
            'id': row['Id'],
            'code': row['Code'],
            'name': row['Name'],
            'colorCode': row['ColorCode']
        })
    
    conn.close()
    return shift_types


@router.put('/api/teams/{team_id:int}/shifttypes', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def update_team_shift_types(request: Request, team_id, data: dict = Depends(parse_json_body)):
    """Update shift types assigned to a team (Admin only)"""
    try:
        shift_type_ids = data.get('shiftTypeIds', [])
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists
        cursor.execute("SELECT Id FROM Teams WHERE Id = ?", (team_id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        # Delete all existing assignments for this team
        cursor.execute("DELETE FROM TeamShiftAssignments WHERE TeamId = ?", (team_id,))
        
        # Insert new assignments
        for shift_type_id in shift_type_ids:
            cursor.execute("""
                INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedBy)
                VALUES (?, ?, ?)
            """, (team_id, shift_type_id, request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'teamId': team_id, 'shiftTypeIds': shift_type_ids}, ensure_ascii=False)
        log_audit(conn, 'TeamShiftAssignment', team_id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update team shift types error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)

