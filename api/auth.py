"""
Authentication Blueprint: login, logout, users, roles, password management.
"""

from flask import Blueprint, jsonify, request, session, current_app
from datetime import datetime, timedelta
import json
import secrets

from .shared import (
    get_db, require_auth, require_role, log_audit, limiter,
    hash_password, verify_password, get_employee_by_email
)

bp = Blueprint('auth', __name__)


@bp.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Authenticate employee and create session"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember_me = data.get('rememberMe', False)
        
        if not email or not password:
            return jsonify({'error': 'Email und Passwort sind erforderlich'}), 400
        
        db = get_db()
        # Get employee from database (employees now have auth data)
        employee = get_employee_by_email(db, email)
        
        if not employee:
            return jsonify({'error': 'Ungültige Anmeldedaten'}), 401
        
        # Check if password is set
        if not employee.get('passwordHash'):
            return jsonify({'error': 'Kein Passwort gesetzt. Bitte Administrator kontaktieren.'}), 401
        
        # Check if account is locked
        if employee['lockoutEnd']:
            lockout_end = datetime.fromisoformat(employee['lockoutEnd'])
            if lockout_end > datetime.utcnow():
                return jsonify({'error': 'Konto ist gesperrt'}), 403
        
        # Verify password
        if not verify_password(password, employee['passwordHash']):
            # Increment failed attempts
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Employees 
                SET AccessFailedCount = AccessFailedCount + 1
                WHERE Id = ?
            """, (employee['id'],))
            conn.commit()
            conn.close()
            
            return jsonify({'error': 'Ungültige Anmeldedaten'}), 401
        
        # Reset failed attempts on successful login and migrate legacy SHA256
        # hash to bcrypt transparently so the next login uses the stronger hash.
        conn = db.get_connection()
        cursor = conn.cursor()
        is_legacy = not (
            employee['passwordHash'].startswith('$2b$') or
            employee['passwordHash'].startswith('$2a$')
        )
        if is_legacy:
            new_hash = hash_password(password)
            cursor.execute(
                "UPDATE Employees SET AccessFailedCount = 0, PasswordHash = ? WHERE Id = ?",
                (new_hash, employee['id']),
            )
        else:
            cursor.execute(
                "UPDATE Employees SET AccessFailedCount = 0 WHERE Id = ?",
                (employee['id'],),
            )
        conn.commit()
        conn.close()
        
        # Create session
        session['user_id'] = employee['id']
        session['user_email'] = employee['email']
        session['user_fullname'] = employee['fullName']
        session['user_roles'] = employee['roles']
        
        if remember_me:
            session.permanent = True
        
        return jsonify({
            'success': True,
            'user': {
                'email': employee['email'],
                'fullName': employee['fullName'],
                'roles': employee['roles']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Anmeldefehler aufgetreten'}), 500


@bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    session.clear()
    return jsonify({'success': True})


@bp.route('/api/auth/current-user', methods=['GET'])
def get_current_user():
    """Get currently authenticated user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'email': session.get('user_email'),
        'fullName': session.get('user_fullname'),
        'roles': session.get('user_roles', [])
    })


@bp.route('/api/users', methods=['GET'])
@require_role('Admin')
def get_all_users():
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
    return jsonify(users)


@bp.route('/api/users/<int:user_id>', methods=['GET'])
@require_role('Admin')
def get_user(user_id):
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
        return jsonify({'error': 'Mitarbeiter/Benutzer nicht gefunden'}), 404
    
    return jsonify({
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
    })


@bp.route('/api/users', methods=['POST'])
@require_role('Admin')
def create_user():
    """Create new employee with authentication credentials (Admin only)"""
    try:
        data = request.get_json()
        
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
            return jsonify({'error': 'Vorname, Name und Personalnummer sind erforderlich'}), 400
        
        if email and not password:
            return jsonify({'error': 'Passwort ist erforderlich wenn E-Mail angegeben wird'}), 400
        
        # Validate roles
        valid_roles = ['Admin', 'Mitarbeiter']
        if not isinstance(roles, list):
            roles = [roles]
        for role in roles:
            if role not in valid_roles:
                return jsonify({'error': f'Ungültige Rolle: {role}. Erlaubt: {", ".join(valid_roles)}'}), 400
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if personalnummer already exists
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ?", (personalnummer,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Personalnummer bereits vorhanden'}), 400
        
        # Check if email already exists
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'E-Mail wird bereits verwendet'}), 400
        
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
        log_audit(conn, 'Employee', employee_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'userId': employee_id, 'employeeId': employee_id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Create employee/user error: {str(e)}")
        return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500


@bp.route('/api/users/<int:user_id>', methods=['PUT'])
@require_role('Admin')
def update_user(user_id):
    """Update employee with authentication data (Admin only)"""
    try:
        data = request.get_json()
        
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
            return jsonify({'error': 'Vorname, Name und Personalnummer sind erforderlich'}), 400
        
        # Validate roles
        valid_roles = ['Admin', 'Mitarbeiter']
        if not isinstance(roles, list):
            roles = [roles]
        for role in roles:
            if role not in valid_roles:
                return jsonify({'error': f'Ungültige Rolle: {role}. Erlaubt: {", ".join(valid_roles)}'}), 400
        
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
            return jsonify({'error': 'Mitarbeiter/Benutzer nicht gefunden'}), 404
        
        # Check if personalnummer is taken by another employee
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ? AND Id != ?", 
                      (personalnummer, user_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Personalnummer bereits von anderem Mitarbeiter verwendet'}), 400
        
        # Check if email is taken by another employee
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ? AND Id != ?", (email, user_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'E-Mail wird bereits verwendet'}), 400
        
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
            log_audit(conn, 'Employee', user_id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update employee/user error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role('Admin')
def delete_user(user_id):
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
            return jsonify({'error': 'Mitarbeiter/Benutzer nicht gefunden'}), 404
        
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
            return jsonify({'error': 'Der letzte Administrator kann nicht gelöscht werden'}), 400
        
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
        log_audit(conn, 'Employee', user_id, 'Deleted', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Delete employee/user error: {str(e)}")
        return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500


@bp.route('/api/roles', methods=['GET'])
@require_role('Admin')
def get_roles():
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
    return jsonify(roles)


@bp.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change password for currently logged in user"""
    try:
        data = request.get_json()
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Aktuelles und neues Passwort sind erforderlich'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'Neues Passwort muss mindestens 8 Zeichen lang sein'}), 400
        
        user_id = session.get('user_id')
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current password hash
        cursor.execute("SELECT PasswordHash FROM Employees WHERE Id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            conn.close()
            return jsonify({'error': 'Benutzer hat kein Passwort gesetzt'}), 400
        
        # Verify current password
        if not verify_password(current_password, row[0]):
            conn.close()
            return jsonify({'error': 'Aktuelles Passwort ist falsch'}), 401
        
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
                 json.dumps({'action': 'User changed own password'}, ensure_ascii=False))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


@bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset link"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'E-Mail-Adresse ist erforderlich'}), 400
        
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
            return jsonify({'success': True, 'message': 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zurücksetzen des Passworts gesendet.'})
        
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
        base_url = request.host_url.rstrip('/')
        
        success, error = send_password_reset_email(
            conn, employee[3], reset_token, employee_name, base_url
        )
        
        conn.close()
        
        if not success:
            current_app.logger.error(f"Failed to send password reset email: {error}")
            # Don't expose email errors to user
        
        return jsonify({'success': True, 'message': 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zurücksetzen des Passworts gesendet.'})
        
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


@bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('newPassword')
        
        if not token or not new_password:
            return jsonify({'error': 'Token und neues Passwort sind erforderlich'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'Passwort muss mindestens 8 Zeichen lang sein'}), 400
        
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
            return jsonify({'error': 'Ungültiger oder bereits verwendeter Token'}), 400
        
        token_id = token_row[0]
        employee_id = token_row[1]
        expires_at = datetime.fromisoformat(token_row[2])
        
        # Check if token is expired
        if expires_at < datetime.utcnow():
            conn.close()
            return jsonify({'error': 'Token ist abgelaufen'}), 400
        
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
                 json.dumps({'action': 'Password reset via email token'}, ensure_ascii=False))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


@bp.route('/api/auth/validate-reset-token', methods=['POST'])
def validate_reset_token():
    """Validate if reset token is valid"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'valid': False})
        
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
            return jsonify({'valid': False})
        
        expires_at = datetime.fromisoformat(row[0])
        if expires_at < datetime.utcnow():
            return jsonify({'valid': False})
        
        return jsonify({'valid': True})
        
    except Exception as e:
        current_app.logger.error(f"Validate reset token error: {str(e)}")
        return jsonify({'valid': False})
