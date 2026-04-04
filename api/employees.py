"""
Employees Blueprint: employees, teams, vacation-periods, rotation groups, CSV import/export.
"""

from flask import Blueprint, jsonify, request, session, current_app, send_file
from datetime import datetime, date
import json
import secrets

from .shared import (
    get_db, require_auth, require_role, log_audit,
    hash_password, _paginate
)

bp = Blueprint('employees', __name__)


@bp.route('/api/employees', methods=['GET'])
def get_employees():
    """Get all employees (now includes authentication data).

    Optional query parameters:
      - page  (int, default 1): 1-based page number
      - limit (int, default 0): items per page; 0 means return all items
    """
    conn = None
    try:
        # Parse pagination parameters
        try:
            page = max(1, int(request.args.get('page', 1)))
            limit = max(0, int(request.args.get('limit', 0)))
        except (ValueError, TypeError):
            return jsonify({'error': 'page and limit must be integers'}), 400

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
            GROUP BY e.Id
            ORDER BY e.Name, e.Vorname
        """)
        
        employees = []
        for row in cursor.fetchall():
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
            return jsonify(_paginate(employees, page, limit))

        return jsonify(employees)
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/api/employees/<int:id>', methods=['GET'])
def get_employee(id):
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
        return jsonify({'error': 'Employee not found'}), 404
    
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
    
    return jsonify({
        'id': row['Id'],
        'vorname': row['Vorname'],
        'name': row['Name'],
        'personalnummer': row['Personalnummer'],
        'email': row['Email'],
        'geburtsdatum': row['Geburtsdatum'],
        'funktion': row['Funktion'],
        'isSpringer': bool(row['IsSpringer']),
        'isFerienjobber': bool(row['IsFerienjobber']),
        'isBrandmeldetechniker': bool(row['IsBrandmeldetechniker']),
        'isBrandschutzbeauftragter': bool(row['IsBrandschutzbeauftragter']),
        'isTdQualified': is_td_qualified,
        'isTeamLeader': is_team_leader,
        'teamId': row['TeamId'],
        'teamName': row['TeamName'],
        'fullName': f"{row['Vorname']} {row['Name']}",
        'roles': row['roles'] if row['roles'] else ''
    })


@bp.route('/api/employees/springers', methods=['GET'])
def get_springers():
    """Get all springers"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.*, t.Name as TeamName
        FROM Employees e
        LEFT JOIN Teams t ON e.TeamId = t.Id
        WHERE e.IsSpringer = 1
        ORDER BY e.Name, e.Vorname
    """)
    
    springers = []
    for row in cursor.fetchall():
        springers.append({
            'id': row['Id'],
            'vorname': row['Vorname'],
            'name': row['Name'],
            'personalnummer': row['Personalnummer'],
            'email': row['Email'],
            'isSpringer': True,
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'fullName': f"{row['Vorname']} {row['Name']}"
        })
    
    conn.close()
    return jsonify(springers)


@bp.route('/api/employees', methods=['POST'])
@require_role('Admin')
def create_employee():
    """Create new employee"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
            return jsonify({'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}), 400
        
        # Validate password - required for new employees
        password = data.get('password')
        if not password:
            return jsonify({'error': 'Passwort ist erforderlich'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Passwort muss mindestens 8 Zeichen lang sein'}), 400
        
        # Validate Funktion field - only allow specific values
        funktion = data.get('funktion')
        if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker', 'Springer']:
            return jsonify({'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker, Springer'}), 400
        
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
            return jsonify({'error': 'Personalnummer bereits vorhanden'}), 400
        
        # Check if email already exists
        email = data.get('email')
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'E-Mail wird bereits verwendet'}), 400
        
        # Hash password
        password_hash = hash_password(password)
        security_stamp = secrets.token_hex(16)
        
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash, SecurityStamp,
             Geburtsdatum, Funktion, 
             IsSpringer, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, TeamId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            1 if data.get('isSpringer') else 0,
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
            current_app.logger.error("Mitarbeiter role not found in database")
            return jsonify({'error': 'System-Fehler: Mitarbeiter-Rolle nicht gefunden'}), 500
        
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
                current_app.logger.error("Admin role not found in database")
                return jsonify({'error': 'System-Fehler: Admin-Rolle nicht gefunden'}), 500
            
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
        log_audit(conn, 'Employee', employee_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': employee_id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Create employee error: {str(e)}")
        return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500


@bp.route('/api/employees/<int:id>', methods=['PUT'])
@require_role('Admin')
def update_employee(id):
    """Update employee"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
            return jsonify({'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}), 400
        
        # Validate password if provided
        password = data.get('password')
        if password and len(password) < 8:
            return jsonify({'error': 'Passwort muss mindestens 8 Zeichen lang sein'}), 400
        
        # Validate Funktion field
        funktion = data.get('funktion')
        if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker', 'Springer']:
            return jsonify({'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker, Springer'}), 400
        
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
                   IsSpringer, IsFerienjobber, IsBrandmeldetechniker, 
                   IsBrandschutzbeauftragter, IsTdQualified, TeamId 
            FROM Employees WHERE Id = ?
        """, (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
        
        # Check if Personalnummer is taken by another employee
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ? AND Id != ?", 
                      (data.get('personalnummer'), id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Personalnummer bereits von anderem Mitarbeiter verwendet'}), 400
        
        # Check if email is taken by another employee
        email = data.get('email')
        if email:
            cursor.execute("SELECT Id FROM Employees WHERE Email = ? AND Id != ?", (email, id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'E-Mail wird bereits verwendet'}), 400
        
        # Update employee with or without password
        if password:
            password_hash = hash_password(password)
            security_stamp = secrets.token_hex(16)
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, NormalizedEmail = ?,
                    PasswordHash = ?, SecurityStamp = ?, Geburtsdatum = ?, 
                    Funktion = ?, IsSpringer = ?, IsFerienjobber = ?, 
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
                1 if data.get('isSpringer') else 0,
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
                    Funktion = ?, IsSpringer = ?, IsFerienjobber = ?, 
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
                1 if data.get('isSpringer') else 0,
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
            current_app.logger.error("Mitarbeiter role not found in database")
            return jsonify({'error': 'System-Fehler: Mitarbeiter-Rolle nicht gefunden'}), 500
        
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
            current_app.logger.error("Admin role not found in database")
            return jsonify({'error': 'System-Fehler: Admin-Rolle nicht gefunden'}), 500
        
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
            log_audit(conn, 'Employee', id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update employee error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/employees/<int:id>', methods=['DELETE'])
@require_role('Admin')
def delete_employee(id):
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
            return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
        
        # Check if employee has assignments
        cursor.execute("SELECT COUNT(*) as count FROM ShiftAssignments WHERE EmployeeId = ?", (id,))
        assignment_count = cursor.fetchone()['count']
        
        if assignment_count > 0:
            conn.close()
            return jsonify({'error': f'Mitarbeiter hat {assignment_count} Schichtzuweisungen und kann nicht gelöscht werden'}), 400
        
        # Delete employee
        cursor.execute("DELETE FROM Employees WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({
            'vorname': emp_row['Vorname'],
            'name': emp_row['Name'],
            'personalnummer': emp_row['Personalnummer']
        }, ensure_ascii=False)
        log_audit(conn, 'Employee', id, 'Deleted', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Delete employee error: {str(e)}")
        return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================

@bp.route('/api/teams', methods=['GET'])
def get_teams():
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
    return jsonify(teams)


@bp.route('/api/teams/<int:id>', methods=['GET'])
def get_team(id):
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
            return jsonify({'error': 'Team nicht gefunden'}), 404
        
        employee_count = int(row['EmployeeCount'])
        
        return jsonify({
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
                            'employeeCount': employee_count
        })
    finally:
        if conn:
            conn.close()


@bp.route('/api/teams', methods=['POST'])
@require_role('Admin')
def create_team():
    """Create new team"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Teamname ist Pflichtfeld'}), 400
        
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
        log_audit(conn, 'Team', team_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': team_id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Create team error: {str(e)}")
        return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500


@bp.route('/api/teams/<int:id>', methods=['PUT'])
@require_role('Admin')
def update_team(id):
    """Update team"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Teamname ist Pflichtfeld'}), 400
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists and get old values for audit
        cursor.execute("SELECT Name, Description, Email FROM Teams WHERE Id = ?", (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({'error': 'Team nicht gefunden'}), 404
        
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
            log_audit(conn, 'Team', id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update team error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/teams/<int:id>', methods=['DELETE'])
@require_role('Admin')
def delete_team(id):
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
            return jsonify({'error': 'Team nicht gefunden'}), 404
        
        # Check if team has employees
        cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE TeamId = ?", (id,))
        employee_count = cursor.fetchone()['count']
        
        if employee_count > 0:
            conn.close()
            return jsonify({'error': f'Team hat {employee_count} Mitarbeiter und kann nicht gelöscht werden'}), 400
        
        # Clear TeamId from AdminNotifications to avoid foreign key constraint violations
        # (AdminNotifications don't have CASCADE delete)
        cursor.execute("UPDATE AdminNotifications SET TeamId = NULL WHERE TeamId = ?", (id,))
        
        # Delete team (TeamShiftAssignments will be automatically deleted due to CASCADE)
        cursor.execute("DELETE FROM Teams WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'name': team_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'Team', id, 'Deleted', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Delete team error: {str(e)}")
        return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500


# ============================================================================
# VACATION PERIODS ENDPOINTS (Ferienzeiten)
# ============================================================================

@bp.route('/api/vacation-periods', methods=['GET'])
def get_vacation_periods():
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
        return jsonify(periods)
        
    except Exception as e:
        current_app.logger.error(f"Get vacation periods error: {str(e)}")
        return jsonify({'error': f'Fehler beim Laden: {str(e)}'}), 500


@bp.route('/api/vacation-periods/<int:id>', methods=['GET'])
def get_vacation_period(id):
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
            return jsonify({'error': 'Ferienzeit nicht gefunden'}), 404
        
        return jsonify({
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
        
    except Exception as e:
        current_app.logger.error(f"Get vacation period error: {str(e)}")
        return jsonify({'error': f'Fehler beim Laden: {str(e)}'}), 500


@bp.route('/api/vacation-periods', methods=['POST'])
@require_role('Admin')
def create_vacation_period():
    """Create new vacation period"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name ist Pflichtfeld'}), 400
        if not data.get('startDate'):
            return jsonify({'error': 'Startdatum ist Pflichtfeld'}), 400
        if not data.get('endDate'):
            return jsonify({'error': 'Enddatum ist Pflichtfeld'}), 400
        
        # Validate dates
        try:
            start_date = date.fromisoformat(data.get('startDate'))
            end_date = date.fromisoformat(data.get('endDate'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Ungültiges Datumsformat'}), 400
        
        if end_date < start_date:
            return jsonify({'error': 'Enddatum muss nach Startdatum liegen'}), 400
        
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
            session.get('user_email')
        ))
        
        period_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'colorCode': data.get('colorCode', '#E8F5E9')
        }, ensure_ascii=False)
        log_audit(conn, 'VacationPeriod', period_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': period_id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Create vacation period error: {str(e)}")
        return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500


@bp.route('/api/vacation-periods/<int:id>', methods=['PUT'])
@require_role('Admin')
def update_vacation_period(id):
    """Update vacation period"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name ist Pflichtfeld'}), 400
        if not data.get('startDate'):
            return jsonify({'error': 'Startdatum ist Pflichtfeld'}), 400
        if not data.get('endDate'):
            return jsonify({'error': 'Enddatum ist Pflichtfeld'}), 400
        
        # Validate dates
        try:
            start_date = date.fromisoformat(data.get('startDate'))
            end_date = date.fromisoformat(data.get('endDate'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Ungültiges Datumsformat'}), 400
        
        if end_date < start_date:
            return jsonify({'error': 'Enddatum muss nach Startdatum liegen'}), 400
        
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
            return jsonify({'error': 'Ferienzeit nicht gefunden'}), 404
        
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
            session.get('user_email'),
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
            log_audit(conn, 'VacationPeriod', id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update vacation period error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/vacation-periods/<int:id>', methods=['DELETE'])
@require_role('Admin')
def delete_vacation_period(id):
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
            return jsonify({'error': 'Ferienzeit nicht gefunden'}), 404
        
        # Delete period
        cursor.execute("DELETE FROM VacationPeriods WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'name': period_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'VacationPeriod', id, 'Deleted', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Delete vacation period error: {str(e)}")
        return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500


# ============================================================================
# ROTATION GROUP ENDPOINTS
# ============================================================================

@bp.route('/api/rotationgroups', methods=['GET'])
def get_rotation_groups():
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
        return jsonify(groups)
        
    except Exception as e:
        current_app.logger.error(f"Get rotation groups error: {str(e)}")
        return jsonify({'error': f'Fehler beim Laden: {str(e)}'}), 500


@bp.route('/api/rotationgroups', methods=['POST'])
@require_role('Admin')
def create_rotation_group():
    """Create new rotation group (Admin only)"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return jsonify({'error': 'Name ist erforderlich'}), 400
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Insert rotation group
        cursor.execute("""
            INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy)
            VALUES (?, ?, ?, ?)
        """, (name, description, 1 if is_active else 0, session.get('user_email', 'system')))
        
        group_id = cursor.lastrowid
        
        # Insert shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (group_id, shift['shiftTypeId'], shift['rotationOrder'], session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', group_id, 'Created', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': group_id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Create rotation group error: {str(e)}")
        return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500


@bp.route('/api/rotationgroups/<int:id>', methods=['GET'])
def get_rotation_group(id):
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
            return jsonify({'error': 'Rotationsgruppe nicht gefunden'}), 404
        
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
        return jsonify(group)
        
    except Exception as e:
        current_app.logger.error(f"Get rotation group error: {str(e)}")
        return jsonify({'error': f'Fehler beim Laden: {str(e)}'}), 500


@bp.route('/api/rotationgroups/<int:id>', methods=['PUT'])
@require_role('Admin')
def update_rotation_group(id):
    """Update rotation group (Admin only)"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return jsonify({'error': 'Name ist erforderlich'}), 400
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT Id FROM RotationGroups WHERE Id = ?", (id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Rotationsgruppe nicht gefunden'}), 404
        
        # Update rotation group
        cursor.execute("""
            UPDATE RotationGroups
            SET Name = ?, Description = ?, IsActive = ?, ModifiedAt = CURRENT_TIMESTAMP, ModifiedBy = ?
            WHERE Id = ?
        """, (name, description, 1 if is_active else 0, session.get('user_email', 'system'), id))
        
        # Delete existing shifts
        cursor.execute("DELETE FROM RotationGroupShifts WHERE RotationGroupId = ?", (id,))
        
        # Insert new shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (id, shift['shiftTypeId'], shift['rotationOrder'], session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', id, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update rotation group error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/rotationgroups/<int:id>', methods=['DELETE'])
@require_role('Admin')
def delete_rotation_group(id):
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
            return jsonify({'error': 'Rotationsgruppe nicht gefunden'}), 404
        
        group_name = row['Name']
        
        # Delete rotation group (cascade will delete shifts)
        cursor.execute("DELETE FROM RotationGroups WHERE Id = ?", (id,))
        
        # Log audit entry
        log_audit(conn, 'RotationGroup', id, 'Deleted', json.dumps({'name': group_name}, ensure_ascii=False))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Delete rotation group error: {str(e)}")
        return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500


# ============================================================================
# DATA EXPORT/IMPORT (Admin only)
# ============================================================================

@bp.route('/api/employees/export/csv', methods=['GET'])
@require_role('Admin')
def export_employees_csv():
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
                   TeamId, IsSpringer, IsFerienjobber, IsBrandmeldetechniker,
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
            'TeamId', 'IsSpringer', 'IsFerienjobber', 'IsBrandmeldetechniker',
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
        
        return send_file(
            output_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'employees_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Export employees error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/teams/export/csv', methods=['GET'])
@require_role('Admin')
def export_teams_csv():
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
        
        return send_file(
            output_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'teams_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Export teams error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/employees/import/csv', methods=['POST'])
@require_role('Admin')
def import_employees_csv():
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
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get conflict mode from query parameter
        conflict_mode = request.args.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return jsonify({'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}), 400
        
        # Read CSV file
        # Try to detect encoding (UTF-8 with BOM, UTF-8, or Latin-1)
        content = file.read()
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
                    'IsSpringer': int(row.get('IsSpringer', 0)),
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
                                Funktion = ?, TeamId = ?, IsSpringer = ?, IsFerienjobber = ?,
                                IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?,
                                IsTdQualified = ?, IsTeamLeader = ?, IsActive = ?
                            WHERE Personalnummer = ?
                        """, (
                            values['Vorname'], values['Name'], values['Email'],
                            values['Geburtsdatum'], values['Funktion'], values['TeamId'],
                            values['IsSpringer'], values['IsFerienjobber'],
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
                         TeamId, IsSpringer, IsFerienjobber, IsBrandmeldetechniker,
                         IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        values['Vorname'], values['Name'], values['Personalnummer'],
                        values['Email'], values['Geburtsdatum'], values['Funktion'],
                        values['TeamId'], values['IsSpringer'], values['IsFerienjobber'],
                        values['IsBrandmeldetechniker'], values['IsBrandschutzbeauftragter'],
                        values['IsTdQualified'], values['IsTeamLeader'], values['IsActive']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        })
        
    except Exception as e:
        current_app.logger.error(f"Import employees error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/teams/import/csv', methods=['POST'])
@require_role('Admin')
def import_teams_csv():
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
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get conflict mode from query parameter
        conflict_mode = request.args.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return jsonify({'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}), 400
        
        # Read CSV file
        content = file.read()
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
                        VALUES (?, ?, ?, ?)
                    """, (
                        values['Name'], values['Description'],
                        values['Email']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        })
        
    except Exception as e:
        current_app.logger.error(f"Import teams error: {str(e)}")
        return jsonify({'error': str(e)}), 500
