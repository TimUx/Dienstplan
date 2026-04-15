"""
Employees Blueprint: employees, teams, vacation-periods, rotation groups, CSV import/export.
"""

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime, date
import json
import secrets
import logging

from .shared import (
    get_db, require_auth, require_role, log_audit,
    hash_password, _paginate, limiter, require_csrf, check_csrf, parse_json_body
)
from .repositories.employee_repository import EmployeeRepository

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
        return JSONResponse(content={'error': f'Database error: {str(e)}'}, status_code=500)
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
        logger.error(f"Create employee error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


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
        logger.error(f"Update employee error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


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
        logger.error(f"Delete employee error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================

@router.get('/api/teams')
def get_teams(request: Request):
    """Get all teams with employee count"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.Id, t.Name, t.Description, t.Email,
               COUNT(e.Id) as EmployeeCount
        FROM Teams t
        LEFT JOIN Employees e ON t.Id = e.TeamId
        GROUP BY t.Id, t.Name, t.Description, t.Email
        ORDER BY t.Name
    """)
    
    teams = []
    for row in cursor.fetchall():
        employee_count = int(row['EmployeeCount'])
        
        teams.append({
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
                            'employeeCount': employee_count
        })
    
    conn.close()
    return teams


@router.get('/api/teams/{id}')
def get_team(request: Request, id: int):
    """Get single team by ID"""
    conn = None
    db = get_db()
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.Id, t.Name, t.Description, t.Email,
                   COUNT(e.Id) as EmployeeCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            WHERE t.Id = ?
            GROUP BY t.Id, t.Name, t.Description, t.Email
        """, (id,))
        
        row = cursor.fetchone()
        
        if not row:
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        employee_count = int(row['EmployeeCount'])
        
        return {
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
                            'employeeCount': employee_count
        }
    finally:
        if conn:
            conn.close()


@router.post('/api/teams', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_team(request: Request, data: dict = Depends(parse_json_body)):
    """Create new team"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Teamname ist Pflichtfeld'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Teams (Name, Description, Email)
            VALUES (?, ?, ?)
        """, (
            data.get('name'),
            data.get('description'),
            data.get('email')
        ))
        
        team_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'description': data.get('description'),
            'email': data.get('email'),
                        }, ensure_ascii=False)
        log_audit(conn, 'Team', team_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': team_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/teams/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_team(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update team"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Teamname ist Pflichtfeld'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists and get old values for audit
        cursor.execute("SELECT Name, Description, Email FROM Teams WHERE Id = ?", (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        cursor.execute("""
            UPDATE Teams 
            SET Name = ?, Description = ?, Email = ?
            WHERE Id = ?
        """, (
            data.get('name'),
            data.get('description'),
            data.get('email'),
            id
        ))
        
        # Log audit entry with changes
        changes_dict = {}
        if old_row['Name'] != data.get('name'):
            changes_dict['name'] = {'old': old_row['Name'], 'new': data.get('name')}
        if old_row['Description'] != data.get('description'):
            changes_dict['description'] = {'old': old_row['Description'], 'new': data.get('description')}
        if old_row['Email'] != data.get('email'):
            changes_dict['email'] = {'old': old_row['Email'], 'new': data.get('email')}
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'Team', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/teams/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_team(request: Request, id: int):
    """Delete team (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists and get info for audit
        cursor.execute("SELECT Name FROM Teams WHERE Id = ?", (id,))
        team_row = cursor.fetchone()
        if not team_row:
            conn.close()
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        # Check if team has employees
        cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE TeamId = ?", (id,))
        employee_count = cursor.fetchone()['count']
        
        if employee_count > 0:
            conn.close()
            return JSONResponse(content={'error': f'Team hat {employee_count} Mitarbeiter und kann nicht gelöscht werden'}, status_code=400)
        
        # Clear TeamId from AdminNotifications to avoid foreign key constraint violations
        # (AdminNotifications don't have CASCADE delete)
        cursor.execute("UPDATE AdminNotifications SET TeamId = NULL WHERE TeamId = ?", (id,))
        
        # Delete team (TeamShiftAssignments will be automatically deleted due to CASCADE)
        cursor.execute("DELETE FROM Teams WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'name': team_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'Team', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# ============================================================================
# VACATION PERIODS ENDPOINTS (Ferienzeiten)
# ============================================================================

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


# ============================================================================
# ROTATION GROUP ENDPOINTS
# ============================================================================

@router.get('/api/rotationgroups')
def get_rotation_groups(request: Request):
    """Get all rotation groups"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, Description, IsActive, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM RotationGroups
            ORDER BY Name
        """)
        
        groups = []
        for row in cursor.fetchall():
            # Get shifts for this group
            cursor.execute("""
                SELECT st.Id, st.Code, st.Name, st.ColorCode, rgs.RotationOrder
                FROM RotationGroupShifts rgs
                INNER JOIN ShiftTypes st ON rgs.ShiftTypeId = st.Id
                WHERE rgs.RotationGroupId = ?
                ORDER BY rgs.RotationOrder
            """, (row['Id'],))
            
            shifts = []
            for shift_row in cursor.fetchall():
                shifts.append({
                    'id': shift_row['Id'],
                    'code': shift_row['Code'],
                    'name': shift_row['Name'],
                    'colorCode': shift_row['ColorCode'],
                    'rotationOrder': shift_row['RotationOrder']
                })
            
            groups.append({
                'id': row['Id'],
                'name': row['Name'],
                'description': row['Description'],
                'isActive': bool(row['IsActive']),
                'shifts': shifts,
                'createdAt': row['CreatedAt'],
                'createdBy': row['CreatedBy'],
                'modifiedAt': row['ModifiedAt'],
                'modifiedBy': row['ModifiedBy']
            })
        
        conn.close()
        return groups
        
    except Exception as e:
        logger.error(f"Get rotation groups error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.post('/api/rotationgroups', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_rotation_group(request: Request, data: dict = Depends(parse_json_body)):
    """Create new rotation group (Admin only)"""
    try:
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return JSONResponse(content={'error': 'Name ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Insert rotation group
        cursor.execute("""
            INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy)
            VALUES (?, ?, ?, ?)
        """, (name, description, 1 if is_active else 0, request.session.get('user_email', 'system')))
        
        group_id = cursor.lastrowid
        
        # Insert shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (group_id, shift['shiftTypeId'], shift['rotationOrder'], request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', group_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': group_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.get('/api/rotationgroups/{id}')
def get_rotation_group(request: Request, id: int):
    """Get single rotation group by ID"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, Description, IsActive, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM RotationGroups
            WHERE Id = ?
        """, (id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        # Get shifts for this group
        cursor.execute("""
            SELECT st.Id, st.Code, st.Name, st.ColorCode, rgs.RotationOrder
            FROM RotationGroupShifts rgs
            INNER JOIN ShiftTypes st ON rgs.ShiftTypeId = st.Id
            WHERE rgs.RotationGroupId = ?
            ORDER BY rgs.RotationOrder
        """, (id,))
        
        shifts = []
        for shift_row in cursor.fetchall():
            shifts.append({
                'id': shift_row['Id'],
                'code': shift_row['Code'],
                'name': shift_row['Name'],
                'colorCode': shift_row['ColorCode'],
                'rotationOrder': shift_row['RotationOrder']
            })
        
        group = {
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'isActive': bool(row['IsActive']),
            'shifts': shifts,
            'createdAt': row['CreatedAt'],
            'createdBy': row['CreatedBy'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        }
        
        conn.close()
        return group
        
    except Exception as e:
        logger.error(f"Get rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.put('/api/rotationgroups/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_rotation_group(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update rotation group (Admin only)"""
    try:
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return JSONResponse(content={'error': 'Name ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT Id FROM RotationGroups WHERE Id = ?", (id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        # Update rotation group
        cursor.execute("""
            UPDATE RotationGroups
            SET Name = ?, Description = ?, IsActive = ?, ModifiedAt = CURRENT_TIMESTAMP, ModifiedBy = ?
            WHERE Id = ?
        """, (name, description, 1 if is_active else 0, request.session.get('user_email', 'system'), id))
        
        # Delete existing shifts
        cursor.execute("DELETE FROM RotationGroupShifts WHERE RotationGroupId = ?", (id,))
        
        # Insert new shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (id, shift['shiftTypeId'], shift['rotationOrder'], request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/rotationgroups/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_rotation_group(request: Request, id: int):
    """Delete rotation group (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT Name FROM RotationGroups WHERE Id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        group_name = row['Name']
        
        # Delete rotation group (cascade will delete shifts)
        cursor.execute("DELETE FROM RotationGroups WHERE Id = ?", (id,))
        
        # Log audit entry
        log_audit(conn, 'RotationGroup', id, 'Deleted', json.dumps({'name': group_name}, ensure_ascii=False), user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)


# ============================================================================
# DATA EXPORT/IMPORT (Admin only)
# ============================================================================

@router.get('/api/employees/export/csv', dependencies=[Depends(require_role('Admin'))])
def export_employees_csv(request: Request):
    """
    Export all employees to CSV format.
    
    Returns a CSV file with all employee data for backup or migration.
    """
    import csv
    from io import StringIO
    
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all employees with their data
        cursor.execute("""
            SELECT Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
                   TeamId, IsFerienjobber, IsBrandmeldetechniker,
                   IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive
            FROM Employees
            WHERE Id > 1
            ORDER BY TeamId, Name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Vorname', 'Name', 'Personalnummer', 'Email', 'Geburtsdatum', 'Funktion',
            'TeamId', 'IsFerienjobber', 'IsBrandmeldetechniker',
            'IsBrandschutzbeauftragter', 'IsTdQualified', 'IsTeamLeader', 'IsActive'
        ])
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        from io import BytesIO
        output_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
        output_bytes.seek(0)
        
        return StreamingResponse(
            output_bytes,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=employees_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Export employees error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.get('/api/teams/export/csv', dependencies=[Depends(require_role('Admin'))])
def export_teams_csv(request: Request):
    """
    Export all teams to CSV format.
    
    Returns a CSV file with all team data for backup or migration.
    """
    import csv
    from io import StringIO
    
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all teams
        cursor.execute("""
            SELECT Name, Description, Email
            FROM Teams
            ORDER BY Name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'Description', 'Email'])
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        from io import BytesIO
        output_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
        output_bytes.seek(0)
        
        return StreamingResponse(
            output_bytes,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=teams_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Export teams error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.post('/api/employees/import/csv', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def import_employees_csv(request: Request, file: UploadFile = File(...)):
    """
    Import employees from CSV file.
    
    Supports conflict resolution:
    - overwrite: Replace existing employees (matched by Personalnummer)
    - skip: Skip existing employees, only add new ones
    
    Query parameters:
    - conflict_mode: 'overwrite' or 'skip' (default: 'skip')
    """
    import csv
    from io import StringIO
    
    try:
        if file.filename == '':
            return JSONResponse(content={'error': 'No file selected'}, status_code=400)
        
        # Get conflict mode from query parameter
        conflict_mode = request.query_params.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return JSONResponse(content={'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}, status_code=400)
        
        # Read CSV file
        # Try to detect encoding (UTF-8 with BOM, UTF-8, or Latin-1)
        content = file.file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        total_rows = 0
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            total_rows += 1
            try:
                # Validate required fields
                required_fields = ['Vorname', 'Name', 'Personalnummer']
                missing_fields = [field for field in required_fields if field not in row or not row[field]]
                if missing_fields:
                    errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                    continue  # Skip to next row
                
                # Check if employee already exists
                cursor.execute("""
                    SELECT Id FROM Employees WHERE Personalnummer = ?
                """, (row['Personalnummer'],))
                
                existing = cursor.fetchone()
                
                # Prepare values with defaults for optional fields
                values = {
                    'Vorname': row['Vorname'],
                    'Name': row['Name'],
                    'Personalnummer': row['Personalnummer'],
                    'Email': row.get('Email', ''),
                    'Geburtsdatum': row.get('Geburtsdatum', None),
                    'Funktion': row.get('Funktion', ''),
                    'TeamId': int(row['TeamId']) if row.get('TeamId') and row['TeamId'].strip() else None,
                    'IsFerienjobber': int(row.get('IsFerienjobber', 0)),
                    'IsBrandmeldetechniker': int(row.get('IsBrandmeldetechniker', 0)),
                    'IsBrandschutzbeauftragter': int(row.get('IsBrandschutzbeauftragter', 0)),
                    'IsTdQualified': int(row.get('IsTdQualified', 0)),
                    'IsTeamLeader': int(row.get('IsTeamLeader', 0)),
                    'IsActive': int(row.get('IsActive', 1))
                }
                
                if existing:
                    if conflict_mode == 'overwrite':
                        # Update existing employee
                        cursor.execute("""
                            UPDATE Employees
                            SET Vorname = ?, Name = ?, Email = ?, Geburtsdatum = ?,
                                Funktion = ?, TeamId = ?, IsFerienjobber = ?,
                                IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?,
                                IsTdQualified = ?, IsTeamLeader = ?, IsActive = ?
                            WHERE Personalnummer = ?
                        """, (
                            values['Vorname'], values['Name'], values['Email'],
                            values['Geburtsdatum'], values['Funktion'], values['TeamId'],
                            values['IsFerienjobber'],
                            values['IsBrandmeldetechniker'], values['IsBrandschutzbeauftragter'],
                            values['IsTdQualified'], values['IsTeamLeader'], values['IsActive'],
                            values['Personalnummer']
                        ))
                        updated_count += 1
                    else:
                        # Skip existing employee
                        skipped_count += 1
                else:
                    # Insert new employee
                    cursor.execute("""
                        INSERT INTO Employees
                        (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
                         TeamId, IsFerienjobber, IsBrandmeldetechniker,
                         IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        values['Vorname'], values['Name'], values['Personalnummer'],
                        values['Email'], values['Geburtsdatum'], values['Funktion'],
                        values['TeamId'], values['IsFerienjobber'],
                        values['IsBrandmeldetechniker'], values['IsBrandschutzbeauftragter'],
                        values['IsTdQualified'], values['IsTeamLeader'], values['IsActive']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Import employees error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.post('/api/teams/import/csv', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def import_teams_csv(request: Request, file: UploadFile = File(...)):
    """
    Import teams from CSV file.
    
    Supports conflict resolution:
    - overwrite: Replace existing teams (matched by Name)
    - skip: Skip existing teams, only add new ones
    
    Query parameters:
    - conflict_mode: 'overwrite' or 'skip' (default: 'skip')
    """
    import csv
    from io import StringIO
    
    try:
        if file.filename == '':
            return JSONResponse(content={'error': 'No file selected'}, status_code=400)
        
        # Get conflict mode from query parameter
        conflict_mode = request.query_params.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return JSONResponse(content={'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}, status_code=400)
        
        # Read CSV file
        content = file.file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        total_rows = 0
        
        for row_num, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                # Validate required fields
                if 'Name' not in row or not row['Name']:
                    errors.append(f"Row {row_num}: Missing required field 'Name'")
                    continue
                
                # Check if team already exists
                cursor.execute("""
                    SELECT Id FROM Teams WHERE Name = ?
                """, (row['Name'],))
                
                existing = cursor.fetchone()
                
                # Prepare values
                values = {
                    'Name': row['Name'],
                    'Description': row.get('Description', ''),
                    'Email': row.get('Email', ''),
                    
                }
                
                if existing:
                    if conflict_mode == 'overwrite':
                        # Update existing team
                        cursor.execute("""
                            UPDATE Teams
                            SET Description = ?, Email = ?
                            WHERE Name = ?
                        """, (
                            values['Description'], values['Email'],
                            values['Name']
                        ))
                        updated_count += 1
                    else:
                        # Skip existing team
                        skipped_count += 1
                else:
                    # Insert new team
                    cursor.execute("""
                        INSERT INTO Teams (Name, Description, Email)
                        VALUES (?, ?, ?)
                    """, (
                        values['Name'], values['Description'],
                        values['Email']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Import teams error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)
