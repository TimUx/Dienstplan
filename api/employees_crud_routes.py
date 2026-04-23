"""Employee list and CRUD API routes."""

import json
import logging
import secrets
from datetime import date, datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .repositories.employee_repository import EmployeeRepository
from .shared import (
    get_db,
    require_role,
    log_audit,
    hash_password,
    _paginate,
    check_csrf,
    parse_json_body,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/employees')
def get_employees(request: Request):
    """Get all employees (now includes authentication data).

    Optional query parameters:
      - page  (int, default 1): 1-based page number
      - limit (int, default 0): items per page; 0 means return all items
    """
    conn = None
    try:
        # Parse pagination parameters
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            limit = max(0, int(request.query_params.get('limit', 0)))
        except (ValueError, TypeError):
            return JSONResponse(content={'error': 'page and limit must be integers'}, status_code=400)

        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        employees = []
        for row in EmployeeRepository.get_all_employees(cursor):
            # Handle fields which may not exist in older databases
            try:
                is_td_qualified = bool(row['IsTdQualified'])
            except (KeyError, IndexError):
                is_td_qualified = False
            
            try:
                is_team_leader = bool(row['IsTeamLeader'])
            except (KeyError, IndexError):
                is_team_leader = False
            
            try:
                is_active = bool(row['IsActive'])
            except (KeyError, IndexError):
                is_active = True
            
            employees.append({
                'id': row['Id'],
                'vorname': row['Vorname'],
                'name': row['Name'],
                'personalnummer': row['Personalnummer'],
                'email': row['Email'],
                'geburtsdatum': row['Geburtsdatum'],
                'funktion': row['Funktion'],
                'isFerienjobber': bool(row['IsFerienjobber']),
                'isBrandmeldetechniker': bool(row['IsBrandmeldetechniker']),
                'isBrandschutzbeauftragter': bool(row['IsBrandschutzbeauftragter']),
                'isTdQualified': is_td_qualified,
                'isTeamLeader': is_team_leader,
                'isActive': is_active,
                'teamId': row['TeamId'],
                'teamName': row['TeamName'],
                'fullName': f"{row['Vorname']} {row['Name']}",
                'hasPassword': bool(row['Email']),  # Has auth if email is set
                'roles': row['roles'].split(',') if row['roles'] else []
            })

        if limit > 0:
            return _paginate(employees, page, limit)

        return employees
    except Exception as e:
        return api_error(
            logger,
            'Datenbankfehler beim Laden der Mitarbeiter',
            status_code=500,
            exc=e,
            context='get_employees failed',
        )
    finally:
        if conn:
            conn.close()


@router.get('/api/employees/{id}')
def get_employee(request: Request, id: int):
    """Get employee by ID"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.*, t.Name as TeamName,
               GROUP_CONCAT(r.Name) as roles
        FROM Employees e
        LEFT JOIN Teams t ON e.TeamId = t.Id
        LEFT JOIN AspNetUserRoles ur ON CAST(e.Id AS TEXT) = ur.UserId
        LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
        WHERE e.Id = ?
        GROUP BY e.Id
    """, (id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return JSONResponse(content={'error': 'Employee not found'}, status_code=404)
    
    # Handle IsTdQualified field which may not exist in older databases
    try:
        is_td_qualified = bool(row['IsTdQualified'])
    except (KeyError, IndexError):
        is_td_qualified = False
    
    # Handle IsTeamLeader field which may not exist in older databases
    try:
        is_team_leader = bool(row['IsTeamLeader'])
    except (KeyError, IndexError):
        is_team_leader = False
    
    return {
        'id': row['Id'],
        'vorname': row['Vorname'],
        'name': row['Name'],
        'personalnummer': row['Personalnummer'],
        'email': row['Email'],
        'geburtsdatum': row['Geburtsdatum'],
        'funktion': row['Funktion'],
        'isFerienjobber': bool(row['IsFerienjobber']),
        'isBrandmeldetechniker': bool(row['IsBrandmeldetechniker']),
        'isBrandschutzbeauftragter': bool(row['IsBrandschutzbeauftragter']),
        'isTdQualified': is_td_qualified,
        'isTeamLeader': is_team_leader,
        'teamId': row['TeamId'],
        'teamName': row['TeamName'],
        'fullName': f"{row['Vorname']} {row['Name']}",
        'roles': row['roles'] if row['roles'] else ''
    }


@router.post('/api/employees', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_employee(request: Request, data: dict = Depends(parse_json_body)):
    """Create new employee"""
    try:
        # Validate required fields
        if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
            return JSONResponse(content={'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}, status_code=400)
        
        # Validate password - required for new employees
        password = data.get('password')
        if not password:
            return JSONResponse(content={'error': 'Passwort ist erforderlich'}, status_code=400)
        
        if len(password) < 8:
            return JSONResponse(content={'error': 'Passwort muss mindestens 8 Zeichen lang sein'}, status_code=400)
        
        # Validate Funktion field - only allow specific values
        funktion = data.get('funktion')
        if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker']:
            return JSONResponse(content={'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker'}, status_code=400)
        
        # Use checkbox values directly from frontend for BMT/BSB flags
        is_bmt = 1 if data.get('isBrandmeldetechniker') else 0
        is_bsb = 1 if data.get('isBrandschutzbeauftragter') else 0
        # TD qualification is automatically set if BMT or BSB is true
        is_td = 1 if (is_bmt or is_bsb) else 0
        is_team_leader = 1 if data.get('isTeamLeader') else 0
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if Personalnummer already exists
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ?", (data.get('personalnummer'),))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Personalnummer bereits vorhanden'}, status_code=400)
        
        # Check if email already exists
        email = data.get('email')
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': 'E-Mail wird bereits verwendet'}, status_code=400)
        
        # Hash password
        password_hash = hash_password(password)
        security_stamp = secrets.token_hex(16)
        
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash, SecurityStamp,
             Geburtsdatum, Funktion, 
             IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, TeamId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('vorname'),
            data.get('name'),
            data.get('personalnummer'),
            email,
            email.upper() if email else None,
            password_hash,
            security_stamp,
            data.get('geburtsdatum'),
            funktion,
            1 if data.get('isFerienjobber') else 0,
            is_bmt,
            is_bsb,
            is_td,
            is_team_leader,
            data.get('teamId')
        ))
        
        employee_id = cursor.lastrowid
        
        # Assign roles: All employees get "Mitarbeiter" role by default
        cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", ('Mitarbeiter',))
        mitarbeiter_role = cursor.fetchone()
        if not mitarbeiter_role:
            conn.close()
            logger.error("Mitarbeiter role not found in database")
            return JSONResponse(content={'error': 'System-Fehler: Mitarbeiter-Rolle nicht gefunden'}, status_code=500)
        
        cursor.execute("""
            INSERT INTO AspNetUserRoles (UserId, RoleId)
            VALUES (?, ?)
        """, (str(employee_id), mitarbeiter_role['Id']))
        
        # If isAdmin flag is set, also assign "Admin" role
        is_admin = data.get('isAdmin', False)
        if is_admin:
            cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", ('Admin',))
            admin_role = cursor.fetchone()
            if not admin_role:
                conn.close()
                logger.error("Admin role not found in database")
                return JSONResponse(content={'error': 'System-Fehler: Admin-Rolle nicht gefunden'}, status_code=500)
            
            cursor.execute("""
                INSERT INTO AspNetUserRoles (UserId, RoleId)
                VALUES (?, ?)
            """, (str(employee_id), admin_role['Id']))
        
        # Log audit entry
        changes = json.dumps({
            'vorname': data.get('vorname'),
            'name': data.get('name'),
            'personalnummer': data.get('personalnummer'),
            'email': data.get('email'),
            'funktion': funktion,
            'teamId': data.get('teamId'),
            'roles': ['Mitarbeiter', 'Admin'] if is_admin else ['Mitarbeiter']
        }, ensure_ascii=False)
        log_audit(conn, 'Employee', employee_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': employee_id}, status_code=201)
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Erstellen des Mitarbeiters',
            status_code=500,
            exc=e,
            context='create_employee failed',
        )


@router.put('/api/employees/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_employee(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update employee"""
    try:
        # Validate required fields
        if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
            return JSONResponse(content={'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}, status_code=400)
        
        # Validate password if provided
        password = data.get('password')
        if password and len(password) < 8:
            return JSONResponse(content={'error': 'Passwort muss mindestens 8 Zeichen lang sein'}, status_code=400)
        
        # Validate Funktion field
        funktion = data.get('funktion')
        if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker']:
            return JSONResponse(content={'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker'}, status_code=400)
        
        # Use checkbox values directly from frontend for BMT/BSB flags
        is_bmt = 1 if data.get('isBrandmeldetechniker') else 0
        is_bsb = 1 if data.get('isBrandschutzbeauftragter') else 0
        # TD qualification is automatically set if BMT or BSB is true
        is_td = 1 if (is_bmt or is_bsb) else 0
        is_team_leader = 1 if data.get('isTeamLeader') else 0
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if employee exists and get old values for audit
        cursor.execute("""
            SELECT Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion, 
                   IsFerienjobber, IsBrandmeldetechniker, 
                   IsBrandschutzbeauftragter, IsTdQualified, TeamId 
            FROM Employees WHERE Id = ?
        """, (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Mitarbeiter nicht gefunden'}, status_code=404)
        
        # Check if Personalnummer is taken by another employee
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ? AND Id != ?", 
                      (data.get('personalnummer'), id))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Personalnummer bereits von anderem Mitarbeiter verwendet'}, status_code=400)
        
        # Check if email is taken by another employee
        email = data.get('email')
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ? AND Id != ?", (email, id))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': 'E-Mail wird bereits verwendet'}, status_code=400)
        
        # Update employee with or without password
        if password:
            password_hash = hash_password(password)
            security_stamp = secrets.token_hex(16)
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, NormalizedEmail = ?,
                    PasswordHash = ?, SecurityStamp = ?, Geburtsdatum = ?, 
                    Funktion = ?, IsFerienjobber = ?, 
                    IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?, IsTdQualified = ?, IsTeamLeader = ?, TeamId = ?
                WHERE Id = ?
            """, (
                data.get('vorname'),
                data.get('name'),
                data.get('personalnummer'),
                email,
                email.upper() if email else None,
                password_hash,
                security_stamp,
                data.get('geburtsdatum'),
                funktion,
                1 if data.get('isFerienjobber') else 0,
                is_bmt,
                is_bsb,
                is_td,
                is_team_leader,
                data.get('teamId'),
                id
            ))
        else:
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, NormalizedEmail = ?, Geburtsdatum = ?, 
                    Funktion = ?, IsFerienjobber = ?, 
                    IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?, IsTdQualified = ?, IsTeamLeader = ?, TeamId = ?
                WHERE Id = ?
            """, (
                data.get('vorname'),
                data.get('name'),
                data.get('personalnummer'),
                email,
                email.upper() if email else None,
                data.get('geburtsdatum'),
                funktion,
                1 if data.get('isFerienjobber') else 0,
                is_bmt,
                is_bsb,
                is_td,
                is_team_leader,
                data.get('teamId'),
                id
            ))
        
        # Update roles: Ensure employee always has "Mitarbeiter" role
        cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", ('Mitarbeiter',))
        mitarbeiter_role = cursor.fetchone()
        if not mitarbeiter_role:
            conn.close()
            logger.error("Mitarbeiter role not found in database")
            return JSONResponse(content={'error': 'System-Fehler: Mitarbeiter-Rolle nicht gefunden'}, status_code=500)
        
        # Check if Mitarbeiter role exists, add if not
        cursor.execute("""
            SELECT 1 FROM AspNetUserRoles 
            WHERE UserId = ? AND RoleId = ?
        """, (str(id), mitarbeiter_role['Id']))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO AspNetUserRoles (UserId, RoleId)
                VALUES (?, ?)
            """, (str(id), mitarbeiter_role['Id']))
        
        # Handle Admin role based on isAdmin flag
        is_admin = data.get('isAdmin', False)
        cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", ('Admin',))
        admin_role = cursor.fetchone()
        
        if not admin_role:
            conn.close()
            logger.error("Admin role not found in database")
            return JSONResponse(content={'error': 'System-Fehler: Admin-Rolle nicht gefunden'}, status_code=500)
        
        # Check if Admin role currently exists for this employee
        cursor.execute("""
            SELECT 1 FROM AspNetUserRoles 
            WHERE UserId = ? AND RoleId = ?
        """, (str(id), admin_role['Id']))
        has_admin_role = cursor.fetchone() is not None
        
        if is_admin and not has_admin_role:
            # Add Admin role
            cursor.execute("""
                INSERT INTO AspNetUserRoles (UserId, RoleId)
                VALUES (?, ?)
            """, (str(id), admin_role['Id']))
        elif not is_admin and has_admin_role:
            # Remove Admin role
            cursor.execute("""
                DELETE FROM AspNetUserRoles 
                WHERE UserId = ? AND RoleId = ?
            """, (str(id), admin_role['Id']))
        
        # Log audit entry with changes
        changes_dict = {}
        if old_row['Vorname'] != data.get('vorname'):
            changes_dict['vorname'] = {'old': old_row['Vorname'], 'new': data.get('vorname')}
        if old_row['Name'] != data.get('name'):
            changes_dict['name'] = {'old': old_row['Name'], 'new': data.get('name')}
        if old_row['Personalnummer'] != data.get('personalnummer'):
            changes_dict['personalnummer'] = {'old': old_row['Personalnummer'], 'new': data.get('personalnummer')}
        if old_row['Email'] != data.get('email'):
            changes_dict['email'] = {'old': old_row['Email'], 'new': data.get('email')}
        if old_row['Funktion'] != funktion:
            changes_dict['funktion'] = {'old': old_row['Funktion'], 'new': funktion}
        if old_row['TeamId'] != data.get('teamId'):
            changes_dict['teamId'] = {'old': old_row['TeamId'], 'new': data.get('teamId')}
        if password:
            changes_dict['password'] = 'changed'
        
        # Track role changes in audit log
        if 'isAdmin' in data:
            # Get old roles for comparison
            cursor.execute("""
                SELECT r.Name FROM AspNetUserRoles ur
                JOIN AspNetRoles r ON ur.RoleId = r.Id
                WHERE ur.UserId = ?
            """, (str(id),))
            old_roles = [row['Name'] for row in cursor.fetchall()]
            new_roles = ['Mitarbeiter']
            if is_admin:
                new_roles.append('Admin')
            
            if set(old_roles) != set(new_roles):
                changes_dict['roles'] = {'old': old_roles, 'new': new_roles}
        
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'Employee', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Aktualisieren des Mitarbeiters',
            status_code=500,
            exc=e,
            context='update_employee failed',
        )


@router.delete('/api/employees/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_employee(request: Request, id: int):
    """Delete employee (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if employee exists and get info for audit
        cursor.execute("SELECT Vorname, Name, Personalnummer FROM Employees WHERE Id = ?", (id,))
        emp_row = cursor.fetchone()
        if not emp_row:
            conn.close()
            return JSONResponse(content={'error': 'Mitarbeiter nicht gefunden'}, status_code=404)
        
        # Check if employee has assignments
        cursor.execute("SELECT COUNT(*) as count FROM ShiftAssignments WHERE EmployeeId = ?", (id,))
        assignment_count = cursor.fetchone()['count']
        
        if assignment_count > 0:
            conn.close()
            return JSONResponse(content={'error': f'Mitarbeiter hat {assignment_count} Schichtzuweisungen und kann nicht gelöscht werden'}, status_code=400)
        
        # Delete employee
        cursor.execute("DELETE FROM Employees WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({
            'vorname': emp_row['Vorname'],
            'name': emp_row['Name'],
            'personalnummer': emp_row['Personalnummer']
        }, ensure_ascii=False)
        log_audit(conn, 'Employee', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Löschen des Mitarbeiters',
            status_code=500,
            exc=e,
            context='delete_employee failed',
        )

