"""
Authentication Router: login, logout, users, roles, password management.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json
import logging
import secrets
import os

from .shared import (
    get_db, require_auth, require_role, log_audit, limiter,
    hash_password, verify_password, get_employee_by_email, require_csrf,
    check_csrf, parse_json_body
)
from .error_utils import api_error

logger = logging.getLogger(__name__)

router = APIRouter()
MAX_FAILED_LOGIN_ATTEMPTS = int(os.environ.get("DIENSTPLAN_MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.environ.get("DIENSTPLAN_LOCKOUT_MINUTES", "15"))


@router.get('/api/csrf-token')
def get_csrf_token(request: Request):
    from .shared import generate_csrf_token
    return {'token': generate_csrf_token(request)}


@router.post('/api/auth/login', dependencies=[Depends(check_csrf)])
def login(request: Request, data: dict = Depends(parse_json_body)):
    """Authenticate employee and create session"""
    try:
        email = data.get('email')
        password = data.get('password')
        remember_me = data.get('rememberMe', False)
        
        if not email or not password:
            return JSONResponse(content={'error': 'Email und Passwort sind erforderlich'}, status_code=400)
        
        db = get_db()
        # Get employee from database (employees now have auth data)
        employee = get_employee_by_email(db, email)
        
        if not employee:
            return JSONResponse(content={'error': 'Ung\u00fcltige Anmeldedaten'}, status_code=401)
        
        # Check if password is set
        if not employee.get('passwordHash'):
            return JSONResponse(content={'error': 'Kein Passwort gesetzt. Bitte Administrator kontaktieren.'}, status_code=401)
        
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check if account is locked; unlock automatically once timeout elapsed.
        if employee['lockoutEnd']:
            lockout_end = datetime.fromisoformat(employee['lockoutEnd'])
            if lockout_end > datetime.utcnow():
                conn.close()
                return JSONResponse(content={'error': 'Konto ist gesperrt'}, status_code=403)
            cursor.execute(
                "UPDATE Employees SET AccessFailedCount = 0, LockoutEnd = NULL WHERE Id = ?",
                (employee['id'],),
            )
            conn.commit()
        
        # Verify password
        if not verify_password(password, employee['passwordHash']):
            # Increment failed attempts and activate lockout once threshold is reached.
            cursor.execute("""
                UPDATE Employees 
                SET AccessFailedCount = AccessFailedCount + 1
                WHERE Id = ?
            """, (employee['id'],))
            cursor.execute("SELECT AccessFailedCount FROM Employees WHERE Id = ?", (employee['id'],))
            failed_count_row = cursor.fetchone()
            failed_count = int(failed_count_row[0]) if failed_count_row else 0
            if failed_count >= MAX_FAILED_LOGIN_ATTEMPTS:
                lockout_end = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                cursor.execute(
                    "UPDATE Employees SET LockoutEnd = ? WHERE Id = ?",
                    (lockout_end.isoformat(), employee['id']),
                )
            conn.commit()
            conn.close()
            if failed_count >= MAX_FAILED_LOGIN_ATTEMPTS:
                return JSONResponse(
                    content={'error': f'Konto ist für {LOCKOUT_MINUTES} Minuten gesperrt'},
                    status_code=403,
                )
            return JSONResponse(content={'error': 'Ung\u00fcltige Anmeldedaten'}, status_code=401)
        
        # Reset failed attempts on successful login and migrate legacy SHA256
        # hash to bcrypt transparently so the next login uses the stronger hash.
        is_legacy = not (
            employee['passwordHash'].startswith('$2b$') or
            employee['passwordHash'].startswith('$2a$')
        )
        if is_legacy:
            new_hash = hash_password(password)
            cursor.execute(
                "UPDATE Employees SET AccessFailedCount = 0, LockoutEnd = NULL, PasswordHash = ? WHERE Id = ?",
                (new_hash, employee['id']),
            )
        else:
            cursor.execute(
                "UPDATE Employees SET AccessFailedCount = 0, LockoutEnd = NULL WHERE Id = ?",
                (employee['id'],),
            )
        conn.commit()
        conn.close()
        
        # Create session
        request.session['user_id'] = employee['id']
        request.session['user_email'] = employee['email']
        request.session['user_fullname'] = employee['fullName']
        request.session['user_roles'] = employee['roles']
        
        if remember_me:
            request.session['_permanent'] = True
        
        conn2 = db.get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT MustChangePassword FROM Employees WHERE Id = ?", (employee['id'],))
        row_mcp = cursor2.fetchone()
        conn2.close()
        must_change = bool(row_mcp and row_mcp[0])

        return {
            'success': True,
            'requiresPasswordChange': must_change,
            'user': {
                'email': employee['email'],
                'fullName': employee['fullName'],
                'roles': employee['roles']
            }
        }
        
    except Exception as e:
        return api_error(
            logger,
            'Anmeldefehler aufgetreten',
            status_code=500,
            exc=e,
            context='Login error',
        )


@router.post('/api/auth/logout', dependencies=[Depends(check_csrf)])
def logout(request: Request):
    """Logout user and clear session"""
    request.session.clear()
    return {'success': True}


@router.get('/api/auth/current-user')
def get_current_user(request: Request):
    """Get currently authenticated user"""
    if 'user_id' not in request.session:
        return JSONResponse(content={'error': 'Not authenticated'}, status_code=401)

    user_roles = request.session.get('user_roles')
    # Session created before user_roles were stored (old cookie) \u2013 reload from DB
    if user_roles is None:
        try:
            db = get_db()
            employee = get_employee_by_email(db, request.session.get('user_email', ''))
            if employee:
                user_roles = employee['roles']
                request.session['user_roles'] = user_roles
                if not request.session.get('user_fullname'):
                    request.session['user_fullname'] = employee['fullName']
            else:
                user_roles = []
        except Exception as e:
            logger.warning(f"Could not reload user roles: {e}")
            user_roles = []

    return {
        'email': request.session.get('user_email'),
        'fullName': request.session.get('user_fullname'),
        'roles': user_roles
    }


@router.get('/api/users', dependencies=[Depends(require_role('Admin'))])
def get_all_users(request: Request):
    """Get all employees with authentication/roles (Admin only)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, e.Personalnummer, e.Email, e.NormalizedEmail,
               e.Funktion, e.TeamId, e.LockoutEnd, e.AccessFailedCount, e.IsActive,
               e.IsFerienjobber, e.IsBrandmeldetechniker, e.IsBrandschutzbeauftragter,
               e.IsTdQualified, e.IsTeamLeader,
               t.Name as TeamName,
               GROUP_CONCAT(r.Name) as roles
        FROM Employees e
        LEFT JOIN Teams t ON e.TeamId = t.Id
        LEFT JOIN AspNetUserRoles ur ON CAST(e.Id AS TEXT) = ur.UserId
        LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
        GROUP BY e.Id
        ORDER BY e.Name, e.Vorname
    """)
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'id': row['Id'],
            'email': row['Email'],
            'vorname': row['Vorname'],
            'name': row['Name'],
            'fullName': f"{row['Vorname']} {row['Name']}",
            'personalnummer': row['Personalnummer'],
            'funktion': row['Funktion'],
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'lockoutEnd': row['LockoutEnd'],
            'accessFailedCount': row['AccessFailedCount'],
            'isActive': bool(row['IsActive']),
            'hasPassword': bool(row['Email']),  # Has auth if email is set
            'roles': row['roles'].split(',') if row['roles'] else [],
            # Employee data
            'isFerienjobber': bool(row['IsFerienjobber']),
            'isBrandmeldetechniker': bool(row['IsBrandmeldetechniker']),
            'isBrandschutzbeauftragter': bool(row['IsBrandschutzbeauftragter']),
            'isTdQualified': bool(row['IsTdQualified']),
            'isTeamLeader': bool(row['IsTeamLeader'])
        })
    
    conn.close()
    return users


@router.get('/api/users/{user_id}', dependencies=[Depends(require_role('Admin'))])
def get_user(request: Request, user_id: int):
    """Get single employee/user by ID (Admin only)"""
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
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return JSONResponse(content={'error': 'Mitarbeiter/Benutzer nicht gefunden'}, status_code=404)
    
    return {
        'id': row['Id'],
        'email': row['Email'],
        'vorname': row['Vorname'],
        'name': row['Name'],
        'fullName': f"{row['Vorname']} {row['Name']}",
        'personalnummer': row['Personalnummer'],
        'funktion': row['Funktion'],
        'teamId': row['TeamId'],
        'teamName': row['TeamName'],
        'lockoutEnd': row['LockoutEnd'],
        'accessFailedCount': row['AccessFailedCount'],
        'isActive': bool(row['IsActive']),
        'roles': row['roles'].split(',') if row['roles'] else [],
        # Employee data
        'isFerienjobber': bool(row['IsFerienjobber']),
        'isBrandmeldetechniker': bool(row['IsBrandmeldetechniker']),
        'isBrandschutzbeauftragter': bool(row['IsBrandschutzbeauftragter']),
        'isTdQualified': bool(row['IsTdQualified']),
        'isTeamLeader': bool(row['IsTeamLeader'])
    }


@router.post('/api/users', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_user(request: Request, data: dict = Depends(parse_json_body)):
    """Create new employee with authentication credentials (Admin only)"""
    try:
        # Required fields
        vorname = data.get('vorname')
        name = data.get('name')
        personalnummer = data.get('personalnummer')
        email = data.get('email')
        password = data.get('password')
        roles = data.get('roles', ['Mitarbeiter'])
        
        # Optional fields
        funktion = data.get('funktion')
        team_id = data.get('teamId')
        geburtsdatum = data.get('geburtsdatum')
        
        # Qualifications
        is_ferienjobber = data.get('isFerienjobber', False)
        is_bmt = data.get('isBrandmeldetechniker', False)
        is_bsb = data.get('isBrandschutzbeauftragter', False)
        is_td_qualified = data.get('isTdQualified', is_bmt or is_bsb)  # Auto-set if BMT or BSB
        is_team_leader = data.get('isTeamLeader', False)
        
        # Validation
        if not vorname or not name or not personalnummer:
            return JSONResponse(content={'error': 'Vorname, Name und Personalnummer sind erforderlich'}, status_code=400)
        
        if email and not password:
            return JSONResponse(content={'error': 'Passwort ist erforderlich wenn E-Mail angegeben wird'}, status_code=400)
        
        # Validate roles
        valid_roles = ['Admin', 'Mitarbeiter', 'Disponent']
        if not isinstance(roles, list):
            roles = [roles]
        for role in roles:
            if role not in valid_roles:
                return JSONResponse(content={'error': f'Ung\u00fcltige Rolle: {role}. Erlaubt: {", ".join(valid_roles)}'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if personalnummer already exists
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ?", (personalnummer,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Personalnummer bereits vorhanden'}, status_code=400)
        
        # Check if email already exists
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': 'E-Mail wird bereits verwendet'}, status_code=400)
        
        # Create employee with authentication data
        password_hash = hash_password(password) if password else None
        security_stamp = secrets.token_hex(16) if password else None
        
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash, SecurityStamp,
             Geburtsdatum, Funktion, TeamId, AccessFailedCount, IsActive,
             IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, 
             IsTdQualified, IsTeamLeader)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?, ?, ?, ?)
        """, (
            vorname, name, personalnummer,
            email, email.upper() if email else None, password_hash, security_stamp,
            geburtsdatum, funktion, team_id,
            1 if is_ferienjobber else 0,
            1 if is_bmt else 0,
            1 if is_bsb else 0,
            1 if is_td_qualified else 0,
            1 if is_team_leader else 0
        ))
        
        employee_id = cursor.lastrowid
        
        # Assign roles (UserId in AspNetUserRoles now contains EmployeeId)
        for role in roles:
            cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", (role,))
            role_row = cursor.fetchone()
            if role_row:
                cursor.execute("""
                    INSERT INTO AspNetUserRoles (UserId, RoleId)
                    VALUES (?, ?)
                """, (str(employee_id), role_row['Id']))
        
        # Log audit entry
        changes = json.dumps({
            'vorname': vorname,
            'name': name,
            'personalnummer': personalnummer,
            'email': email,
            'funktion': funktion,
            'teamId': team_id,
            'roles': roles
        }, ensure_ascii=False)
        log_audit(conn, 'Employee', employee_id, 'Created', changes,
                  user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'userId': employee_id, 'employeeId': employee_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create employee/user error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/users/{user_id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_user(request: Request, user_id: int, data: dict = Depends(parse_json_body)):
    """Update employee with authentication data (Admin only)"""
    try:
        # Employee data
        vorname = data.get('vorname')
        name = data.get('name')
        personalnummer = data.get('personalnummer')
        email = data.get('email')
        password = data.get('password')  # Optional password change
        funktion = data.get('funktion')
        team_id = data.get('teamId')
        geburtsdatum = data.get('geburtsdatum')
        roles = data.get('roles', [])
        
        # Qualifications
        is_ferienjobber = data.get('isFerienjobber', False)
        is_bmt = data.get('isBrandmeldetechniker', False)
        is_bsb = data.get('isBrandschutzbeauftragter', False)
        is_td_qualified = data.get('isTdQualified', is_bmt or is_bsb)
        is_team_leader = data.get('isTeamLeader', False)
        
        # Validation
        if not vorname or not name or not personalnummer:
            return JSONResponse(content={'error': 'Vorname, Name und Personalnummer sind erforderlich'}, status_code=400)
        
        # Validate roles
        valid_roles = ['Admin', 'Mitarbeiter', 'Disponent']
        if not isinstance(roles, list):
            roles = [roles]
        for role in roles:
            if role not in valid_roles:
                return JSONResponse(content={'error': f'Ung\u00fcltige Rolle: {role}. Erlaubt: {", ".join(valid_roles)}'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if employee exists
        cursor.execute("""
            SELECT Vorname, Name, Personalnummer, Email, Funktion, TeamId
            FROM Employees WHERE Id = ?
        """, (user_id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Mitarbeiter/Benutzer nicht gefunden'}, status_code=404)
        
        # Check if personalnummer is taken by another employee
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ? AND Id != ?", 
                      (personalnummer, user_id))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Personalnummer bereits von anderem Mitarbeiter verwendet'}, status_code=400)
        
        # Check if email is taken by another employee
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ? AND Id != ?", (email, user_id))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': 'E-Mail wird bereits verwendet'}, status_code=400)
        
        # Update employee
        if password:
            password_hash = hash_password(password)
            security_stamp = secrets.token_hex(16)
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, NormalizedEmail = ?,
                    PasswordHash = ?, SecurityStamp = ?, Geburtsdatum = ?, Funktion = ?, TeamId = ?,
                    IsFerienjobber = ?, IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?,
                    IsTdQualified = ?, IsTeamLeader = ?
                WHERE Id = ?
            """, (
                vorname, name, personalnummer, email, email.upper() if email else None,
                password_hash, security_stamp, geburtsdatum, funktion, team_id,
                1 if is_ferienjobber else 0, 1 if is_bmt else 0, 1 if is_bsb else 0,
                1 if is_td_qualified else 0, 1 if is_team_leader else 0,
                user_id
            ))
        else:
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, NormalizedEmail = ?,
                    Geburtsdatum = ?, Funktion = ?, TeamId = ?,
                    IsFerienjobber = ?, IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?,
                    IsTdQualified = ?, IsTeamLeader = ?
                WHERE Id = ?
            """, (
                vorname, name, personalnummer, email, email.upper() if email else None,
                geburtsdatum, funktion, team_id,
                1 if is_ferienjobber else 0, 1 if is_bmt else 0, 1 if is_bsb else 0,
                1 if is_td_qualified else 0, 1 if is_team_leader else 0,
                user_id
            ))
        
        # Update roles - delete old roles and insert new ones
        cursor.execute("DELETE FROM AspNetUserRoles WHERE UserId = ?", (str(user_id),))
        for role in roles:
            cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", (role,))
            role_row = cursor.fetchone()
            if role_row:
                cursor.execute("""
                    INSERT INTO AspNetUserRoles (UserId, RoleId)
                    VALUES (?, ?)
                """, (str(user_id), role_row['Id']))
        
        # Log audit entry with changes
        changes_dict = {}
        if old_row['Vorname'] != vorname:
            changes_dict['vorname'] = {'old': old_row['Vorname'], 'new': vorname}
        if old_row['Name'] != name:
            changes_dict['name'] = {'old': old_row['Name'], 'new': name}
        if old_row['Personalnummer'] != personalnummer:
            changes_dict['personalnummer'] = {'old': old_row['Personalnummer'], 'new': personalnummer}
        if old_row['Email'] != email:
            changes_dict['email'] = {'old': old_row['Email'], 'new': email}
        changes_dict['roles'] = roles
        if password:
            changes_dict['passwordChanged'] = True
        
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'Employee', user_id, 'Updated', changes,
                      user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update employee/user error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/users/{user_id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_user(request: Request, user_id: int):
    """Delete employee/user (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if employee exists and get info for audit
        cursor.execute("SELECT Vorname, Name, Email FROM Employees WHERE Id = ?", (user_id,))
        employee_row = cursor.fetchone()
        if not employee_row:
            conn.close()
            return JSONResponse(content={'error': 'Mitarbeiter/Benutzer nicht gefunden'}, status_code=404)
        
        # Prevent deleting the last admin
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM Employees e
            JOIN AspNetUserRoles ur ON CAST(e.Id AS TEXT) = ur.UserId
            JOIN AspNetRoles r ON ur.RoleId = r.Id
            WHERE r.Name = 'Admin'
        """)
        admin_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as is_admin
            FROM AspNetUserRoles ur
            JOIN AspNetRoles r ON ur.RoleId = r.Id
            WHERE ur.UserId = ? AND r.Name = 'Admin'
        """, (str(user_id),))
        is_admin = cursor.fetchone()['is_admin'] > 0
        
        if is_admin and admin_count <= 1:
            conn.close()
            return JSONResponse(content={'error': 'Der letzte Administrator kann nicht gel\u00f6scht werden'}, status_code=400)
        
        # Delete roles first (foreign key constraint)
        cursor.execute("DELETE FROM AspNetUserRoles WHERE UserId = ?", (str(user_id),))
        
        # Delete employee (cascade will handle related data)
        cursor.execute("DELETE FROM Employees WHERE Id = ?", (user_id,))
        
        # Log audit entry
        changes = json.dumps({
            'vorname': employee_row['Vorname'],
            'name': employee_row['Name'],
            'email': employee_row['Email']
        }, ensure_ascii=False)
        log_audit(conn, 'Employee', user_id, 'Deleted', changes,
                  user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete employee/user error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim L\u00f6schen: {str(e)}'}, status_code=500)


@router.get('/api/roles', dependencies=[Depends(require_role('Admin'))])
def get_roles(request: Request):
    """Get all available roles (Admin only)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT Id, Name FROM AspNetRoles ORDER BY Name")
    
    roles = []
    for row in cursor.fetchall():
        roles.append({
            'id': row['Id'],
            'name': row['Name']
        })
    
    conn.close()
    return roles


@router.post('/api/auth/change-password', dependencies=[Depends(require_auth), Depends(check_csrf)])
def change_password(request: Request, data: dict = Depends(parse_json_body)):
    """Change password for currently logged in user"""
    try:
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return JSONResponse(content={'error': 'Aktuelles und neues Passwort sind erforderlich'}, status_code=400)
        
        if len(new_password) < 8:
            return JSONResponse(content={'error': 'Neues Passwort muss mindestens 8 Zeichen lang sein'}, status_code=400)
        
        user_id = request.session.get('user_id')
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current password hash
        cursor.execute("SELECT PasswordHash FROM Employees WHERE Id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            conn.close()
            return JSONResponse(content={'error': 'Benutzer hat kein Passwort gesetzt'}, status_code=400)
        
        # Verify current password
        if not verify_password(current_password, row[0]):
            conn.close()
            return JSONResponse(content={'error': 'Aktuelles Passwort ist falsch'}, status_code=401)
        
        # Update password
        new_password_hash = hash_password(new_password)
        security_stamp = secrets.token_hex(16)
        
        cursor.execute("""
            UPDATE Employees
            SET PasswordHash = ?, SecurityStamp = ?
            WHERE Id = ?
        """, (new_password_hash, security_stamp, user_id))
        
        # Log audit entry
        log_audit(conn, 'Employee', user_id, 'PasswordChanged', 
                 json.dumps({'action': 'User changed own password'}, ensure_ascii=False),
                 user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        cursor.execute("UPDATE Employees SET MustChangePassword = 0 WHERE Id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)


@router.post('/api/auth/forgot-password', dependencies=[Depends(check_csrf)])
def forgot_password(request: Request, data: dict = Depends(parse_json_body)):
    """Request password reset link"""
    try:
        email = data.get('email')
        
        if not email:
            return JSONResponse(content={'error': 'E-Mail-Adresse ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Find employee by email
        cursor.execute("""
            SELECT Id, Vorname, Name, Email
            FROM Employees
            WHERE Email = ? AND PasswordHash IS NOT NULL
        """, (email,))
        
        employee = cursor.fetchone()
        
        # Always return success to prevent email enumeration
        if not employee:
            conn.close()
            return {'success': True, 'message': 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zur\u00fccksetzen des Passworts gesendet.'}
        
        # Generate reset token
        import secrets as sec
        reset_token = sec.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Store reset token
        cursor.execute("""
            INSERT INTO PasswordResetTokens (EmployeeId, Token, ExpiresAt)
            VALUES (?, ?, ?)
        """, (employee[0], reset_token, expires_at))
        
        conn.commit()
        
        # Send reset email
        from email_service import send_password_reset_email
        employee_name = f"{employee[1]} {employee[2]}"
        base_url = str(request.base_url).rstrip('/')
        
        success, error = send_password_reset_email(
            conn, employee[3], reset_token, employee_name, base_url
        )
        
        conn.close()
        
        if not success:
            logger.error(f"Failed to send password reset email: {error}")
            # Don't expose email errors to user
        
        return {'success': True, 'message': 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zur\u00fccksetzen des Passworts gesendet.'}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)


@router.post('/api/auth/reset-password', dependencies=[Depends(check_csrf)])
def reset_password(request: Request, data: dict = Depends(parse_json_body)):
    """Reset password using token"""
    try:
        token = data.get('token')
        new_password = data.get('newPassword')
        
        if not token or not new_password:
            return JSONResponse(content={'error': 'Token und neues Passwort sind erforderlich'}, status_code=400)
        
        if len(new_password) < 8:
            return JSONResponse(content={'error': 'Passwort muss mindestens 8 Zeichen lang sein'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Find valid token
        cursor.execute("""
            SELECT Id, EmployeeId, ExpiresAt
            FROM PasswordResetTokens
            WHERE Token = ? AND IsUsed = 0
        """, (token,))
        
        token_row = cursor.fetchone()
        
        if not token_row:
            conn.close()
            return JSONResponse(content={'error': 'Ung\u00fcltiger oder bereits verwendeter Token'}, status_code=400)
        
        token_id = token_row[0]
        employee_id = token_row[1]
        expires_at = datetime.fromisoformat(token_row[2])
        
        # Check if token is expired
        if expires_at < datetime.utcnow():
            conn.close()
            return JSONResponse(content={'error': 'Token ist abgelaufen'}, status_code=400)
        
        # Update password
        new_password_hash = hash_password(new_password)
        security_stamp = secrets.token_hex(16)
        
        cursor.execute("""
            UPDATE Employees
            SET PasswordHash = ?, SecurityStamp = ?, AccessFailedCount = 0, LockoutEnd = NULL
            WHERE Id = ?
        """, (new_password_hash, security_stamp, employee_id))
        
        # Mark token as used
        cursor.execute("""
            UPDATE PasswordResetTokens
            SET IsUsed = 1, UsedAt = ?
            WHERE Id = ?
        """, (datetime.utcnow().isoformat(), token_id))
        
        # Log audit entry
        log_audit(conn, 'Employee', employee_id, 'PasswordReset', 
                 json.dumps({'action': 'Password reset via email token'}, ensure_ascii=False),
                 user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)


@router.post('/api/auth/validate-reset-token', dependencies=[Depends(check_csrf)])
def validate_reset_token(request: Request, data: dict = Depends(parse_json_body)):
    """Validate if reset token is valid"""
    try:
        token = data.get('token')
        
        if not token:
            return {'valid': False}
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ExpiresAt
            FROM PasswordResetTokens
            WHERE Token = ? AND IsUsed = 0
        """, (token,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'valid': False}
        
        expires_at = datetime.fromisoformat(row[0])
        if expires_at < datetime.utcnow():
            return {'valid': False}
        
        return {'valid': True}
        
    except Exception as e:
        logger.error(f"Validate reset token error: {str(e)}")
        return {'valid': False}
