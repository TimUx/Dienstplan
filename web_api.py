"""
Flask Web API for shift planning system.
Provides REST API endpoints compatible with the existing .NET Web UI.
"""

from flask import Flask, jsonify, request, send_file, session
from flask_cors import CORS
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import sqlite3
import json
import hashlib
import secrets
from functools import wraps

# PDF export dependencies
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

from data_loader import load_from_database, get_existing_assignments
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import Employee, Team, Absence, AbsenceType, ShiftAssignment


class Database:
    """Database connection helper"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def hash_password(password: str) -> str:
    """
    Hash password using SHA256.
    
    Note: This is a simple implementation for development/migration from .NET.
    For production, consider using bcrypt, scrypt, or Argon2 for better security.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash


def get_user_by_email(db, email: str) -> Optional[Dict]:
    """Get user by email"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.*, GROUP_CONCAT(r.Name) as roles
        FROM AspNetUsers u
        LEFT JOIN AspNetUserRoles ur ON u.Id = ur.UserId
        LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
        WHERE u.Email = ?
        GROUP BY u.Id
    """, (email,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        'id': row['Id'],
        'email': row['Email'],
        'passwordHash': row['PasswordHash'],
        'fullName': row['FullName'],
        'lockoutEnd': row['LockoutEnd'],
        'accessFailedCount': row['AccessFailedCount'],
        'roles': row['roles'].split(',') if row['roles'] else []
    }


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(*required_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_roles = session.get('user_roles', [])
            if not any(role in user_roles for role in required_roles):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_audit(conn, entity_name: str, entity_id: str, action: str, changes: Optional[str] = None, 
              user_id: Optional[str] = None, user_name: Optional[str] = None):
    """
    Log an audit entry to the AuditLogs table.
    
    Args:
        conn: Database connection (must be already opened)
        entity_name: Name of the entity (e.g., 'Employee', 'Team', 'ShiftAssignment', 'Absence')
        entity_id: ID of the entity being modified
        action: Action performed (e.g., 'Create', 'Update', 'Delete')
        changes: Optional JSON string with details of changes
        user_id: Optional user ID (will try to get from session if not provided)
        user_name: Optional user name (will try to get from session if not provided)
    
    Note: Audit logging failures are logged but do not prevent the main operation from succeeding.
    """
    try:
        cursor = conn.cursor()
        
        # Get user info from session if not provided
        if user_id is None:
            user_id = session.get('user_id')
        if user_name is None:
            user_name = session.get('user_email')
        
        cursor.execute("""
            INSERT INTO AuditLogs (Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_id,
            user_name,
            entity_name,
            str(entity_id),
            action,
            changes
        ))
    except Exception as e:
        # Log the audit failure but don't raise - we don't want audit logging to break business operations
        import sys
        print(f"Warning: Failed to log audit entry: {e}", file=sys.stderr)


def create_app(db_path: str = "dienstplan.db") -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Configured Flask app
    """
    app = Flask(__name__, static_folder='wwwroot', static_url_path='')
    
    # Configure session
    # Use a consistent secret key (in production, load from environment variable)
    import os
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_NAME'] = 'dienstplan_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    CORS(app, supports_credentials=True)  # Enable CORS with credentials
    
    db = Database(db_path)
    
    # ============================================================================
    # AUTHENTICATION ENDPOINTS
    # ============================================================================
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Authenticate user and create session"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            remember_me = data.get('rememberMe', False)
            
            if not email or not password:
                return jsonify({'error': 'Email und Passwort sind erforderlich'}), 400
            
            # Get user from database
            user = get_user_by_email(db, email)
            
            if not user:
                return jsonify({'error': 'Ungültige Anmeldedaten'}), 401
            
            # Check if account is locked
            if user['lockoutEnd']:
                lockout_end = datetime.fromisoformat(user['lockoutEnd'])
                if lockout_end > datetime.utcnow():
                    return jsonify({'error': 'Konto ist gesperrt'}), 403
            
            # Verify password
            if not verify_password(password, user['passwordHash']):
                # Increment failed attempts
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE AspNetUsers 
                    SET AccessFailedCount = AccessFailedCount + 1
                    WHERE Id = ?
                """, (user['id'],))
                conn.commit()
                conn.close()
                
                return jsonify({'error': 'Ungültige Anmeldedaten'}), 401
            
            # Reset failed attempts on successful login
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AspNetUsers 
                SET AccessFailedCount = 0
                WHERE Id = ?
            """, (user['id'],))
            conn.commit()
            conn.close()
            
            # Create session
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_fullname'] = user['fullName']
            session['user_roles'] = user['roles']
            
            if remember_me:
                session.permanent = True
            
            return jsonify({
                'success': True,
                'user': {
                    'email': user['email'],
                    'fullName': user['fullName'],
                    'roles': user['roles']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Anmeldefehler aufgetreten'}), 500
    
    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        """Logout user and clear session"""
        session.clear()
        return jsonify({'success': True})
    
    @app.route('/api/auth/current-user', methods=['GET'])
    def get_current_user():
        """Get currently authenticated user"""
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        return jsonify({
            'email': session.get('user_email'),
            'fullName': session.get('user_fullname'),
            'roles': session.get('user_roles', [])
        })
    
    @app.route('/api/auth/users', methods=['GET'])
    @require_role('Admin')
    def get_users():
        """Get all users (Admin only)"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.Id, u.Email, u.FullName, u.LockoutEnd, u.AccessFailedCount,
                   GROUP_CONCAT(r.Name) as roles
            FROM AspNetUsers u
            LEFT JOIN AspNetUserRoles ur ON u.Id = ur.UserId
            LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
            GROUP BY u.Id
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row['Id'],
                'email': row['Email'],
                'fullName': row['FullName'],
                'lockoutEnd': row['LockoutEnd'],
                'accessFailedCount': row['AccessFailedCount'],
                'roles': row['roles'].split(',') if row['roles'] else []
            })
        
        conn.close()
        return jsonify(users)
    
    @app.route('/api/auth/register', methods=['POST'])
    @require_role('Admin')
    def register_user():
        """Register new user (Admin only)"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            full_name = data.get('fullName')
            role = data.get('role', 'Mitarbeiter')
            
            if not email or not password:
                return jsonify({'error': 'Email und Passwort sind erforderlich'}), 400
            
            # Check if user already exists
            existing_user = get_user_by_email(db, email)
            if existing_user:
                return jsonify({'error': 'Benutzer existiert bereits'}), 400
            
            # Create user
            user_id = secrets.token_hex(16)
            password_hash = hash_password(password)
            security_stamp = secrets.token_hex(16)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO AspNetUsers (Id, Email, NormalizedEmail, PasswordHash, SecurityStamp, FullName)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, email.upper(), password_hash, security_stamp, full_name))
            
            # Assign role
            cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = ?", (role,))
            role_row = cursor.fetchone()
            if role_row:
                cursor.execute("""
                    INSERT INTO AspNetUserRoles (UserId, RoleId)
                    VALUES (?, ?)
                """, (user_id, role_row['Id']))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'userId': user_id})
            
        except Exception as e:
            app.logger.error(f"Register error: {str(e)}")
            return jsonify({'error': 'Registrierungsfehler'}), 500
    
    # ============================================================================
    # EMPLOYEE ENDPOINTS
    # ============================================================================
    
    @app.route('/api/employees', methods=['GET'])
    def get_employees():
        """Get all employees"""
        conn = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.*, t.Name as TeamName
                FROM Employees e
                LEFT JOIN Teams t ON e.TeamId = t.Id
                ORDER BY e.Name, e.Vorname
            """)
            
            employees = []
            for row in cursor.fetchall():
                # Handle IsTdQualified field which may not exist in older databases
                try:
                    is_td_qualified = bool(row['IsTdQualified'])
                except (KeyError, IndexError):
                    is_td_qualified = False
                
                employees.append({
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
                    'teamId': row['TeamId'],
                    'teamName': row['TeamName'],
                    'fullName': f"{row['Vorname']} {row['Name']}"
                })
            
            return jsonify(employees)
        except Exception as e:
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            if conn:
                conn.close()
    
    @app.route('/api/employees/<int:id>', methods=['GET'])
    def get_employee(id):
        """Get employee by ID"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.*, t.Name as TeamName
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.Id
            WHERE e.Id = ?
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
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'fullName': f"{row['Vorname']} {row['Name']}"
        })
    
    @app.route('/api/employees/springers', methods=['GET'])
    def get_springers():
        """Get all springers"""
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
    
    @app.route('/api/employees', methods=['POST'])
    @require_role('Admin', 'Disponent')
    def create_employee():
        """Create new employee"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
                return jsonify({'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}), 400
            
            # Validate Funktion field - only allow specific values
            funktion = data.get('funktion')
            if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker', 'Springer']:
                return jsonify({'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker, Springer'}), 400
            
            # Use checkbox values directly from frontend for BMT/BSB flags
            is_bmt = 1 if data.get('isBrandmeldetechniker') else 0
            is_bsb = 1 if data.get('isBrandschutzbeauftragter') else 0
            # TD qualification is automatically set if BMT or BSB is true
            is_td = 1 if (is_bmt or is_bsb) else 0
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if Personalnummer already exists
            cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ?", (data.get('personalnummer'),))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Personalnummer bereits vorhanden'}), 400
            
            cursor.execute("""
                INSERT INTO Employees 
                (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion, 
                 IsSpringer, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, IsTdQualified, TeamId)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('vorname'),
                data.get('name'),
                data.get('personalnummer'),
                data.get('email'),
                data.get('geburtsdatum'),
                funktion,
                1 if data.get('isSpringer') else 0,
                1 if data.get('isFerienjobber') else 0,
                is_bmt,
                is_bsb,
                is_td,
                data.get('teamId')
            ))
            
            employee_id = cursor.lastrowid
            
            # Log audit entry
            changes = json.dumps({
                'vorname': data.get('vorname'),
                'name': data.get('name'),
                'personalnummer': data.get('personalnummer'),
                'email': data.get('email'),
                'funktion': funktion,
                'teamId': data.get('teamId')
            }, ensure_ascii=False)
            log_audit(conn, 'Employee', employee_id, 'Create', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': employee_id}), 201
            
        except Exception as e:
            app.logger.error(f"Create employee error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/employees/<int:id>', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def update_employee(id):
        """Update employee"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('vorname') or not data.get('name') or not data.get('personalnummer'):
                return jsonify({'error': 'Vorname, Name und Personalnummer sind Pflichtfelder'}), 400
            
            # Validate Funktion field
            funktion = data.get('funktion')
            if funktion and funktion not in ['Brandmeldetechniker', 'Brandschutzbeauftragter', 'Techniker', 'Springer']:
                return jsonify({'error': 'Ungültige Funktion. Erlaubt: Brandmeldetechniker, Brandschutzbeauftragter, Techniker, Springer'}), 400
            
            # Use checkbox values directly from frontend for BMT/BSB flags
            is_bmt = 1 if data.get('isBrandmeldetechniker') else 0
            is_bsb = 1 if data.get('isBrandschutzbeauftragter') else 0
            # TD qualification is automatically set if BMT or BSB is true
            is_td = 1 if (is_bmt or is_bsb) else 0
            
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
            
            cursor.execute("""
                UPDATE Employees 
                SET Vorname = ?, Name = ?, Personalnummer = ?, Email = ?, Geburtsdatum = ?, 
                    Funktion = ?, IsSpringer = ?, IsFerienjobber = ?, 
                    IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?, IsTdQualified = ?, TeamId = ?
                WHERE Id = ?
            """, (
                data.get('vorname'),
                data.get('name'),
                data.get('personalnummer'),
                data.get('email'),
                data.get('geburtsdatum'),
                funktion,
                1 if data.get('isSpringer') else 0,
                1 if data.get('isFerienjobber') else 0,
                is_bmt,
                is_bsb,
                is_td,
                data.get('teamId'),
                id
            ))
            
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
            
            if changes_dict:
                changes = json.dumps(changes_dict, ensure_ascii=False)
                log_audit(conn, 'Employee', id, 'Update', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Update employee error: {str(e)}")
            return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500
    
    @app.route('/api/employees/<int:id>', methods=['DELETE'])
    @require_role('Admin')
    def delete_employee(id):
        """Delete employee (Admin only)"""
        try:
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
            log_audit(conn, 'Employee', id, 'Delete', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Delete employee error: {str(e)}")
            return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500
    
    # ============================================================================
    # TEAM ENDPOINTS
    # ============================================================================
    
    @app.route('/api/teams', methods=['GET'])
    def get_teams():
        """Get all teams with employee count"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.Id, t.Name, t.Description, t.Email, t.IsVirtual,
                   COUNT(e.Id) as EmployeeCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            GROUP BY t.Id, t.Name, t.Description, t.Email, t.IsVirtual
            ORDER BY t.Name
        """)
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'id': row['Id'],
                'name': row['Name'],
                'description': row['Description'],
                'email': row['Email'],
                'isVirtual': bool(row['IsVirtual']),
                'employeeCount': row['EmployeeCount']
            })
        
        conn.close()
        return jsonify(teams)
    
    @app.route('/api/teams/<int:id>', methods=['GET'])
    def get_team(id):
        """Get single team by ID"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.Id, t.Name, t.Description, t.Email, t.IsVirtual,
                   COUNT(e.Id) as EmployeeCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            WHERE t.Id = ?
            GROUP BY t.Id, t.Name, t.Description, t.Email, t.IsVirtual
        """, (id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Team nicht gefunden'}), 404
        
        return jsonify({
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
            'isVirtual': bool(row['IsVirtual']),
            'employeeCount': row['EmployeeCount']
        })
    
    @app.route('/api/teams', methods=['POST'])
    @require_role('Admin', 'Disponent')
    def create_team():
        """Create new team"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name'):
                return jsonify({'error': 'Teamname ist Pflichtfeld'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO Teams (Name, Description, Email, IsVirtual)
                VALUES (?, ?, ?, ?)
            """, (
                data.get('name'),
                data.get('description'),
                data.get('email'),
                1 if data.get('isVirtual') else 0
            ))
            
            team_id = cursor.lastrowid
            
            # Log audit entry
            changes = json.dumps({
                'name': data.get('name'),
                'description': data.get('description'),
                'email': data.get('email'),
                'isVirtual': data.get('isVirtual')
            }, ensure_ascii=False)
            log_audit(conn, 'Team', team_id, 'Create', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': team_id}), 201
            
        except Exception as e:
            app.logger.error(f"Create team error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/teams/<int:id>', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def update_team(id):
        """Update team"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name'):
                return jsonify({'error': 'Teamname ist Pflichtfeld'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if team exists and get old values for audit
            cursor.execute("SELECT Name, Description, Email, IsVirtual FROM Teams WHERE Id = ?", (id,))
            old_row = cursor.fetchone()
            if not old_row:
                conn.close()
                return jsonify({'error': 'Team nicht gefunden'}), 404
            
            cursor.execute("""
                UPDATE Teams 
                SET Name = ?, Description = ?, Email = ?, IsVirtual = ?
                WHERE Id = ?
            """, (
                data.get('name'),
                data.get('description'),
                data.get('email'),
                1 if data.get('isVirtual') else 0,
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
            new_is_virtual = 1 if data.get('isVirtual') else 0
            if old_row['IsVirtual'] != new_is_virtual:
                changes_dict['isVirtual'] = {'old': bool(old_row['IsVirtual']), 'new': bool(new_is_virtual)}
            
            if changes_dict:
                changes = json.dumps(changes_dict, ensure_ascii=False)
                log_audit(conn, 'Team', id, 'Update', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Update team error: {str(e)}")
            return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500
    
    @app.route('/api/teams/<int:id>', methods=['DELETE'])
    @require_role('Admin')
    def delete_team(id):
        """Delete team (Admin only)"""
        try:
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
            
            # Delete team
            cursor.execute("DELETE FROM Teams WHERE Id = ?", (id,))
            
            # Log audit entry
            changes = json.dumps({'name': team_row['Name']}, ensure_ascii=False)
            log_audit(conn, 'Team', id, 'Delete', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Delete team error: {str(e)}")
            return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500
    
    # ============================================================================
    # SHIFT TYPE ENDPOINTS
    # ============================================================================
    
    @app.route('/api/shifttypes', methods=['GET'])
    def get_shift_types():
        """Get all shift types"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ShiftTypes ORDER BY Id")
        
        shift_types = []
        for row in cursor.fetchall():
            shift_types.append({
                'id': row['Id'],
                'code': row['Code'],
                'name': row['Name'],
                'startTime': row['StartTime'],
                'endTime': row['EndTime'],
                'colorCode': row['ColorCode']
            })
        
        conn.close()
        return jsonify(shift_types)
    
    # ============================================================================
    # SHIFT PLANNING ENDPOINTS
    # ============================================================================
    
    @app.route('/api/shifts/schedule', methods=['GET'])
    def get_schedule():
        """Get shift schedule for a date range"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        view = request.args.get('view', 'week')
        
        if not start_date_str:
            return jsonify({'error': 'startDate is required'}), 400
        
        # Validate and parse dates
        try:
            start_date = date.fromisoformat(start_date_str)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid startDate format. Use YYYY-MM-DD'}), 400
        
        # Calculate end date based on view
        if not end_date_str:
            if view == 'week':
                end_date = start_date + timedelta(days=6)
            elif view == 'month':
                # Get last day of month
                if start_date.month == 12:
                    end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
            elif view == 'year':
                end_date = date(start_date.year, 12, 31)
            else:
                end_date = start_date + timedelta(days=30)
        else:
            try:
                end_date = date.fromisoformat(end_date_str)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid endDate format. Use YYYY-MM-DD'}), 400
        
        conn = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get assignments
            cursor.execute("""
                SELECT sa.*, e.Vorname, e.Name, e.TeamId, e.IsSpringer,
                       st.Code, st.Name as ShiftName, st.ColorCode
                FROM ShiftAssignments sa
                JOIN Employees e ON sa.EmployeeId = e.Id
                JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                ORDER BY sa.Date, e.TeamId, e.Name, e.Vorname
            """, (start_date.isoformat(), end_date.isoformat()))
            
            assignments = []
            for row in cursor.fetchall():
                assignments.append({
                    'id': row['Id'],
                    'employeeId': row['EmployeeId'],
                    'employeeName': f"{row['Vorname']} {row['Name']}",
                    'teamId': row['TeamId'],
                    'isSpringer': bool(row['IsSpringer']),
                    'shiftTypeId': row['ShiftTypeId'],
                    'shiftCode': row['Code'],
                    'shiftName': row['ShiftName'],
                    'colorCode': row['ColorCode'],
                    'date': row['Date'],
                    'isManual': bool(row['IsManual']),
                    'isSpringerAssignment': bool(row['IsSpringerAssignment']),
                    'isFixed': bool(row['IsFixed']),
                    'notes': row['Notes']
                })
            
            # Get absences from Absences table
            cursor.execute("""
                SELECT a.*, e.Vorname, e.Name, e.TeamId
                FROM Absences a
                JOIN Employees e ON a.EmployeeId = e.Id
                WHERE (a.StartDate <= ? AND a.EndDate >= ?)
                   OR (a.StartDate >= ? AND a.StartDate <= ?)
            """, (end_date.isoformat(), start_date.isoformat(), 
                  start_date.isoformat(), end_date.isoformat()))
            
            absences = []
            for row in cursor.fetchall():
                absences.append({
                    'id': row['Id'],
                    'employeeId': row['EmployeeId'],
                    'employeeName': f"{row['Vorname']} {row['Name']}",
                    'teamId': row['TeamId'],
                    'type': ['', 'Krank', 'Urlaub', 'Lehrgang'][row['Type']],
                    'startDate': row['StartDate'],
                    'endDate': row['EndDate'],
                    'notes': row['Notes']
                })
            
            # Also get approved vacation requests and add them as absences
            cursor.execute("""
                SELECT vr.Id, vr.EmployeeId, vr.StartDate, vr.EndDate, vr.Notes,
                       e.Vorname, e.Name, e.TeamId
                FROM VacationRequests vr
                JOIN Employees e ON vr.EmployeeId = e.Id
                WHERE vr.Status = 'Genehmigt'
                  AND ((vr.StartDate <= ? AND vr.EndDate >= ?)
                   OR (vr.StartDate >= ? AND vr.StartDate <= ?))
            """, (end_date.isoformat(), start_date.isoformat(),
                  start_date.isoformat(), end_date.isoformat()))
            
            vacation_id_offset = 10000  # Offset to avoid ID conflicts
            for row in cursor.fetchall():
                absences.append({
                    'id': vacation_id_offset + row['Id'],
                    'employeeId': row['EmployeeId'],
                    'employeeName': f"{row['Vorname']} {row['Name']}",
                    'teamId': row['TeamId'],
                    'type': 'Urlaub',
                    'startDate': row['StartDate'],
                    'endDate': row['EndDate'],
                    'notes': row['Notes'] or 'Genehmigter Urlaub'
                })
            
            return jsonify({
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'assignments': assignments,
                'absences': absences
            })
            
        except Exception as e:
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            if conn:
                conn.close()
    
    @app.route('/api/shifts/plan', methods=['POST'])
    def plan_shifts():
        """Automatic shift planning using OR-Tools"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        force = request.args.get('force', 'false').lower() == 'true'
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'startDate and endDate are required'}), 400
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Load data
            employees, teams, absences = load_from_database(db.db_path)
            
            # Create model
            planning_model = create_shift_planning_model(
                employees, teams, start_date, end_date, absences
            )
            
            # Solve
            result = solve_shift_planning(planning_model, time_limit_seconds=300)
            
            if not result:
                return jsonify({'error': 'No solution found'}), 500
            
            assignments, special_functions, complete_schedule = result
            
            # Save to database
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Delete existing non-fixed assignments if force
            if force:
                cursor.execute("""
                    DELETE FROM ShiftAssignments 
                    WHERE Date >= ? AND Date <= ? AND IsFixed = 0
                """, (start_date.isoformat(), end_date.isoformat()))
            
            # Insert new assignments
            for assignment in assignments:
                cursor.execute("""
                    INSERT INTO ShiftAssignments 
                    (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    assignment.employee_id,
                    assignment.shift_type_id,
                    assignment.date.isoformat(),
                    0,
                    1 if assignment.is_springer_assignment else 0,
                    0,
                    datetime.utcnow().isoformat(),
                    "Python-OR-Tools"
                ))
            
            # Insert special functions (TD assignments)
            # Get TD shift type ID
            cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'TD'")
            td_row = cursor.fetchone()
            if td_row:
                td_shift_type_id = td_row[0]
                for (emp_id, date_obj), function_code in special_functions.items():
                    if function_code == "TD":
                        cursor.execute("""
                            INSERT INTO ShiftAssignments 
                            (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            emp_id,
                            td_shift_type_id,
                            date_obj.isoformat(),
                            0,
                            0,
                            0,
                            datetime.utcnow().isoformat(),
                            "Python-OR-Tools"
                        ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Successfully planned {len(assignments)} shifts',
                'assignmentsCount': len(assignments),
                'specialFunctionsCount': len(special_functions)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/shifts/assignments/<int:id>', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def update_shift_assignment(id):
        """Update a shift assignment (manual edit)"""
        try:
            data = request.get_json()
            
            # Validate data types
            try:
                employee_id = int(data.get('employeeId'))
                shift_type_id = int(data.get('shiftTypeId'))
                assignment_date = date.fromisoformat(data.get('date'))
            except (ValueError, TypeError) as e:
                return jsonify({'error': f'Ungültige Daten: {str(e)}'}), 400
            
            conn = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Check if assignment exists and get old values for audit
                cursor.execute("""
                    SELECT EmployeeId, ShiftTypeId, Date, IsFixed, Notes 
                    FROM ShiftAssignments WHERE Id = ?
                """, (id,))
                old_row = cursor.fetchone()
                if not old_row:
                    return jsonify({'error': 'Schichtzuweisung nicht gefunden'}), 404
                
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
                    session.get('user_email'),
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
                    log_audit(conn, 'ShiftAssignment', id, 'Update', changes)
                
                conn.commit()
                
                return jsonify({'success': True})
                
            finally:
                if conn:
                    conn.close()
            
        except Exception as e:
            app.logger.error(f"Update shift assignment error: {str(e)}")
            return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500
    
    @app.route('/api/shifts/assignments', methods=['POST'])
    @require_role('Admin', 'Disponent')
    def create_shift_assignment():
        """Create a shift assignment manually"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('employeeId') or not data.get('shiftTypeId') or not data.get('date'):
                return jsonify({'error': 'EmployeeId, ShiftTypeId und Date sind erforderlich'}), 400
            
            # Validate data types
            try:
                employee_id = int(data.get('employeeId'))
                shift_type_id = int(data.get('shiftTypeId'))
                assignment_date = date.fromisoformat(data.get('date'))
            except (ValueError, TypeError) as e:
                return jsonify({'error': f'Ungültige Daten: {str(e)}'}), 400
            
            conn = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Check for existing assignment (same employee, date, shift type)
                cursor.execute("""
                    SELECT Id FROM ShiftAssignments 
                    WHERE EmployeeId = ? AND Date = ? AND ShiftTypeId = ?
                """, (employee_id, assignment_date.isoformat(), shift_type_id))
                
                if cursor.fetchone():
                    return jsonify({'error': 'Diese Schichtzuweisung existiert bereits'}), 400
                
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
                    session.get('user_email')
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
                log_audit(conn, 'ShiftAssignment', assignment_id, 'Create', changes)
                
                conn.commit()
                
                return jsonify({'success': True, 'id': assignment_id}), 201
                
            finally:
                if conn:
                    conn.close()
            
        except Exception as e:
            app.logger.error(f"Create shift assignment error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/shifts/assignments/<int:id>', methods=['DELETE'])
    @require_role('Admin', 'Disponent')
    def delete_shift_assignment(id):
        """Delete a shift assignment"""
        try:
            conn = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Check if assignment exists and get info for audit
                cursor.execute("""
                    SELECT EmployeeId, ShiftTypeId, Date, IsFixed 
                    FROM ShiftAssignments WHERE Id = ?
                """, (id,))
                row = cursor.fetchone()
                
                if not row:
                    return jsonify({'error': 'Schichtzuweisung nicht gefunden'}), 404
                
                # Warn if trying to delete a fixed assignment
                if row['IsFixed']:
                    return jsonify({'error': 'Fixierte Schichtzuweisungen können nicht gelöscht werden. Bitte erst entsperren.'}), 400
                
                # Delete assignment
                cursor.execute("DELETE FROM ShiftAssignments WHERE Id = ?", (id,))
                
                # Log audit entry
                changes = json.dumps({
                    'employeeId': row['EmployeeId'],
                    'shiftTypeId': row['ShiftTypeId'],
                    'date': row['Date']
                }, ensure_ascii=False)
                log_audit(conn, 'ShiftAssignment', id, 'Delete', changes)
                
                conn.commit()
                
                return jsonify({'success': True})
                
            finally:
                if conn:
                    conn.close()
            
        except Exception as e:
            app.logger.error(f"Delete shift assignment error: {str(e)}")
            return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500
    
    @app.route('/api/shifts/assignments/<int:id>/toggle-fixed', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def toggle_fixed_assignment(id):
        """Toggle the IsFixed flag on an assignment (lock/unlock)"""
        try:
            conn = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Check if assignment exists
                cursor.execute("SELECT Id, IsFixed FROM ShiftAssignments WHERE Id = ?", (id,))
                row = cursor.fetchone()
                
                if not row:
                    return jsonify({'error': 'Schichtzuweisung nicht gefunden'}), 404
                
                # Toggle fixed status
                new_fixed_status = 0 if row['IsFixed'] else 1
                
                cursor.execute("""
                    UPDATE ShiftAssignments 
                    SET IsFixed = ?, ModifiedAt = ?, ModifiedBy = ?
                    WHERE Id = ?
                """, (
                    new_fixed_status,
                    datetime.utcnow().isoformat(),
                    session.get('user_email'),
                    id
                ))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'isFixed': bool(new_fixed_status)
                })
                
            finally:
                if conn:
                    conn.close()
            
        except Exception as e:
            app.logger.error(f"Toggle fixed assignment error: {str(e)}")
            return jsonify({'error': f'Fehler beim Sperren/Entsperren: {str(e)}'}), 500
    
    @app.route('/api/shifts/export/csv', methods=['GET'])
    def export_schedule_csv():
        """Export schedule to CSV format"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'startDate and endDate are required'}), 400
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get assignments
            cursor.execute("""
                SELECT sa.Date, e.Vorname, e.Name, e.Personalnummer, 
                       t.Name as TeamName, st.Code, st.Name as ShiftName
                FROM ShiftAssignments sa
                JOIN Employees e ON sa.EmployeeId = e.Id
                LEFT JOIN Teams t ON e.TeamId = t.Id
                JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                ORDER BY sa.Date, t.Name, e.Name, e.Vorname
            """, (start_date.isoformat(), end_date.isoformat()))
            
            # Build CSV
            import io
            output = io.StringIO()
            output.write("Datum,Team,Mitarbeiter,Personalnummer,Schichttyp,Schichtname\n")
            
            for row in cursor.fetchall():
                team_name = row['TeamName'] or 'Ohne Team'
                output.write(f"{row['Date']},{team_name},{row['Vorname']} {row['Name']},{row['Personalnummer']},{row['Code']},{row['ShiftName']}\n")
            
            conn.close()
            
            # Return as downloadable file
            from flask import make_response
            csv_data = output.getvalue()
            output.close()
            
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=Dienstplan_{start_date_str}_bis_{end_date_str}.csv'
            return response
            
        except Exception as e:
            app.logger.error(f"CSV export error: {str(e)}")
            return jsonify({'error': f'Export-Fehler: {str(e)}'}), 500
    
    @app.route('/api/shifts/export/pdf', methods=['GET'])
    def export_schedule_pdf():
        """Export schedule to PDF format"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'startDate and endDate are required'}), 400
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get assignments
            cursor.execute("""
                SELECT sa.Date, e.Vorname, e.Name, e.Personalnummer, 
                       t.Name as TeamName, st.Code, st.Name as ShiftName
                FROM ShiftAssignments sa
                JOIN Employees e ON sa.EmployeeId = e.Id
                LEFT JOIN Teams t ON e.TeamId = t.Id
                JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                ORDER BY sa.Date, t.Name, e.Name, e.Vorname
            """, (start_date.isoformat(), end_date.isoformat()))
            
            # Create PDF
            import io
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
            elements = []
            
            # Title
            styles = getSampleStyleSheet()
            title = Paragraph(f"Dienstplan {start_date_str} bis {end_date_str}", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 0.5*cm))
            
            # Table data
            data = [['Datum', 'Team', 'Mitarbeiter', 'Personalnummer', 'Schichttyp', 'Schichtname']]
            for row in cursor.fetchall():
                team_name = row['TeamName'] or 'Ohne Team'
                data.append([
                    row['Date'],
                    team_name,
                    f"{row['Vorname']} {row['Name']}",
                    row['Personalnummer'],
                    row['Code'],
                    row['ShiftName']
                ])
            
            conn.close()
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            # Return PDF
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'Dienstplan_{start_date_str}_bis_{end_date_str}.pdf'
            )
            
        except Exception as e:
            app.logger.error(f"PDF export error: {str(e)}")
            return jsonify({'error': f'PDF-Export-Fehler: {str(e)}'}), 500
    
    @app.route('/api/shifts/export/excel', methods=['GET'])
    def export_schedule_excel():
        """Export schedule to Excel format"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'startDate and endDate are required'}), 400
        
        try:
            # Import Excel library
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment
            except ImportError:
                return jsonify({
                    'error': 'Excel-Export erfordert openpyxl. Bitte installieren Sie es mit: pip install openpyxl'
                }), 501
            
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get assignments
            cursor.execute("""
                SELECT sa.Date, e.Vorname, e.Name, e.Personalnummer, 
                       t.Name as TeamName, st.Code, st.Name as ShiftName
                FROM ShiftAssignments sa
                JOIN Employees e ON sa.EmployeeId = e.Id
                LEFT JOIN Teams t ON e.TeamId = t.Id
                JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                ORDER BY sa.Date, t.Name, e.Name, e.Vorname
            """, (start_date.isoformat(), end_date.isoformat()))
            
            # Create workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Dienstplan"
            
            # Header
            headers = ['Datum', 'Team', 'Mitarbeiter', 'Personalnummer', 'Schichttyp', 'Schichtname']
            ws.append(headers)
            
            # Style header
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            # Add data
            for row in cursor.fetchall():
                team_name = row['TeamName'] or 'Ohne Team'
                ws.append([
                    row['Date'],
                    team_name,
                    f"{row['Vorname']} {row['Name']}",
                    row['Personalnummer'],
                    row['Code'],
                    row['ShiftName']
                ])
            
            conn.close()
            
            # Adjust column widths
            for column in ws.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except Exception:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column[0].column_letter].width = adjusted_width
            
            # Save to BytesIO
            import io
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            # Return Excel file
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'Dienstplan_{start_date_str}_bis_{end_date_str}.xlsx'
            )
            
        except Exception as e:
            app.logger.error(f"Excel export error: {str(e)}")
            return jsonify({'error': f'Excel-Export-Fehler: {str(e)}'}), 500
    
    # ============================================================================
    # ABSENCE ENDPOINTS
    # ============================================================================
    
    @app.route('/api/absences', methods=['GET'])
    def get_absences():
        """Get all absences"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, e.Vorname, e.Name, e.TeamId
            FROM Absences a
            JOIN Employees e ON a.EmployeeId = e.Id
            ORDER BY a.StartDate DESC
        """)
        
        absences = []
        for row in cursor.fetchall():
            # Map type: 1=AU (Krank), 2=U (Urlaub), 3=L (Lehrgang)
            type_names = ['', 'Krank / AU', 'Urlaub', 'Lehrgang']
            absences.append({
                'id': row['Id'],
                'employeeId': row['EmployeeId'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'type': type_names[row['Type']] if row['Type'] < len(type_names) else 'Unbekannt',
                'startDate': row['StartDate'],
                'endDate': row['EndDate'],
                'notes': row['Notes'],
                'createdAt': row['CreatedAt']
            })
        
        conn.close()
        return jsonify(absences)
    
    @app.route('/api/absences', methods=['POST'])
    @require_role('Admin', 'Disponent')
    def create_absence():
        """Create new absence (AU or Lehrgang)"""
        try:
            data = request.get_json()
            
            if not data.get('employeeId') or not data.get('type') or not data.get('startDate') or not data.get('endDate'):
                return jsonify({'error': 'EmployeeId, Type, StartDate und EndDate sind erforderlich'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO Absences 
                (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt, CreatedBy)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('employeeId'),
                data.get('type'),
                data.get('startDate'),
                data.get('endDate'),
                data.get('notes'),
                datetime.utcnow().isoformat(),
                session.get('user_email')
            ))
            
            absence_id = cursor.lastrowid
            
            # Log audit entry
            changes = json.dumps({
                'employeeId': data.get('employeeId'),
                'type': data.get('type'),
                'startDate': data.get('startDate'),
                'endDate': data.get('endDate'),
                'notes': data.get('notes')
            }, ensure_ascii=False)
            log_audit(conn, 'Absence', absence_id, 'Create', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': absence_id}), 201
            
        except Exception as e:
            app.logger.error(f"Create absence error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/absences/<int:id>', methods=['DELETE'])
    @require_role('Admin', 'Disponent')
    def delete_absence(id):
        """Delete an absence"""
        try:
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
                return jsonify({'error': 'Abwesenheit nicht gefunden'}), 404
            
            cursor.execute("DELETE FROM Absences WHERE Id = ?", (id,))
            
            # Log audit entry
            changes = json.dumps({
                'employeeId': absence_row['EmployeeId'],
                'type': absence_row['Type'],
                'startDate': absence_row['StartDate'],
                'endDate': absence_row['EndDate']
            }, ensure_ascii=False)
            log_audit(conn, 'Absence', id, 'Delete', changes)
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Delete absence error: {str(e)}")
            return jsonify({'error': f'Fehler beim Löschen: {str(e)}'}), 500
    
    # ============================================================================
    # VACATION REQUEST ENDPOINTS
    # ============================================================================
    
    @app.route('/api/vacationrequests', methods=['GET'])
    def get_vacation_requests():
        """Get all vacation requests or pending ones"""
        status_filter = request.args.get('status')
        
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
        return jsonify(requests)
    
    @app.route('/api/vacationrequests', methods=['POST'])
    @require_auth
    def create_vacation_request():
        """Create new vacation request"""
        try:
            data = request.get_json()
            
            if not data.get('employeeId') or not data.get('startDate') or not data.get('endDate'):
                return jsonify({'error': 'EmployeeId, StartDate und EndDate sind erforderlich'}), 400
            
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
                session.get('user_email')
            ))
            
            request_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': request_id}), 201
            
        except Exception as e:
            app.logger.error(f"Create vacation request error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/vacationrequests/<int:id>/status', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def update_vacation_request_status(id):
        """Update vacation request status (Disponent only)"""
        try:
            data = request.get_json()
            status = data.get('status')
            response = data.get('response')
            
            if status not in ['Genehmigt', 'Abgelehnt', 'InBearbeitung']:
                return jsonify({'error': 'Ungültiger Status'}), 400
            
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
                session.get('user_email'),
                id
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Update vacation request error: {str(e)}")
            return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500
    
    # ============================================================================
    # SHIFT EXCHANGE ENDPOINTS
    # ============================================================================
    
    @app.route('/api/shiftexchanges/available', methods=['GET'])
    def get_available_shift_exchanges():
        """Get available shift exchanges"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT se.*, 
                   sa.Date, sa.ShiftTypeId,
                   st.Code as ShiftCode, st.Name as ShiftName,
                   e.Vorname, e.Name, e.TeamId
            FROM ShiftExchanges se
            JOIN ShiftAssignments sa ON se.ShiftAssignmentId = sa.Id
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            JOIN Employees e ON se.OfferingEmployeeId = e.Id
            WHERE se.Status = 'Angeboten'
            ORDER BY sa.Date
        """)
        
        exchanges = []
        for row in cursor.fetchall():
            exchanges.append({
                'id': row['Id'],
                'shiftAssignmentId': row['ShiftAssignmentId'],
                'offeringEmployeeId': row['OfferingEmployeeId'],
                'offeringEmployeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'date': row['Date'],
                'shiftCode': row['ShiftCode'],
                'shiftName': row['ShiftName'],
                'status': row['Status'],
                'offeringReason': row['OfferingReason'],
                'createdAt': row['CreatedAt']
            })
        
        conn.close()
        return jsonify(exchanges)
    
    @app.route('/api/shiftexchanges/pending', methods=['GET'])
    @require_role('Admin', 'Disponent')
    def get_pending_shift_exchanges():
        """Get pending shift exchanges (Disponent only)"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT se.*, 
                   sa.Date, sa.ShiftTypeId,
                   st.Code as ShiftCode, st.Name as ShiftName,
                   e1.Vorname as OfferingVorname, e1.Name as OfferingName,
                   e2.Vorname as RequestingVorname, e2.Name as RequestingName
            FROM ShiftExchanges se
            JOIN ShiftAssignments sa ON se.ShiftAssignmentId = sa.Id
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            JOIN Employees e1 ON se.OfferingEmployeeId = e1.Id
            LEFT JOIN Employees e2 ON se.RequestingEmployeeId = e2.Id
            WHERE se.Status = 'Angefragt'
            ORDER BY sa.Date
        """)
        
        exchanges = []
        for row in cursor.fetchall():
            exchanges.append({
                'id': row['Id'],
                'shiftAssignmentId': row['ShiftAssignmentId'],
                'offeringEmployeeId': row['OfferingEmployeeId'],
                'offeringEmployeeName': f"{row['OfferingVorname']} {row['OfferingName']}",
                'requestingEmployeeId': row['RequestingEmployeeId'],
                'requestingEmployeeName': f"{row['RequestingVorname']} {row['RequestingName']}" if row['RequestingEmployeeId'] else None,
                'date': row['Date'],
                'shiftCode': row['ShiftCode'],
                'shiftName': row['ShiftName'],
                'status': row['Status'],
                'offeringReason': row['OfferingReason'],
                'createdAt': row['CreatedAt']
            })
        
        conn.close()
        return jsonify(exchanges)
    
    @app.route('/api/shiftexchanges', methods=['POST'])
    @require_auth
    def create_shift_exchange():
        """Create new shift exchange offer"""
        try:
            data = request.get_json()
            
            if not data.get('shiftAssignmentId') or not data.get('offeringEmployeeId'):
                return jsonify({'error': 'ShiftAssignmentId und OfferingEmployeeId sind erforderlich'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ShiftExchanges 
                (ShiftAssignmentId, OfferingEmployeeId, Status, OfferingReason, CreatedAt)
                VALUES (?, ?, 'Angeboten', ?, ?)
            """, (
                data.get('shiftAssignmentId'),
                data.get('offeringEmployeeId'),
                data.get('offeringReason'),
                datetime.utcnow().isoformat()
            ))
            
            exchange_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': exchange_id}), 201
            
        except Exception as e:
            app.logger.error(f"Create shift exchange error: {str(e)}")
            return jsonify({'error': f'Fehler beim Erstellen: {str(e)}'}), 500
    
    @app.route('/api/shiftexchanges/<int:id>/request', methods=['POST'])
    @require_auth
    def request_shift_exchange(id):
        """Request a shift exchange"""
        try:
            data = request.get_json()
            requesting_employee_id = data.get('requestingEmployeeId')
            
            if not requesting_employee_id:
                return jsonify({'error': 'RequestingEmployeeId ist erforderlich'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ShiftExchanges 
                SET RequestingEmployeeId = ?, Status = 'Angefragt'
                WHERE Id = ? AND Status = 'Angeboten'
            """, (requesting_employee_id, id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'Tauschangebot nicht verfügbar'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Request shift exchange error: {str(e)}")
            return jsonify({'error': f'Fehler beim Anfragen: {str(e)}'}), 500
    
    @app.route('/api/shiftexchanges/<int:id>/process', methods=['PUT'])
    @require_role('Admin', 'Disponent')
    def process_shift_exchange(id):
        """Process shift exchange (approve/reject)"""
        try:
            data = request.get_json()
            status = data.get('status')
            notes = data.get('notes')
            
            if status not in ['Genehmigt', 'Abgelehnt']:
                return jsonify({'error': 'Status muss Genehmigt oder Abgelehnt sein'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get exchange details
            cursor.execute("""
                SELECT ShiftAssignmentId, OfferingEmployeeId, RequestingEmployeeId
                FROM ShiftExchanges
                WHERE Id = ? AND Status = 'Angefragt'
            """, (id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return jsonify({'error': 'Tauschangebot nicht gefunden oder bereits bearbeitet'}), 404
            
            shift_assignment_id = row['ShiftAssignmentId']
            requesting_employee_id = row['RequestingEmployeeId']
            
            # Update exchange status
            cursor.execute("""
                UPDATE ShiftExchanges 
                SET Status = ?, DisponentNotes = ?, ProcessedAt = ?, ProcessedBy = ?
                WHERE Id = ?
            """, (
                status,
                notes,
                datetime.utcnow().isoformat(),
                session.get('user_email'),
                id
            ))
            
            # If approved, update the shift assignment
            if status == 'Genehmigt' and requesting_employee_id:
                cursor.execute("""
                    UPDATE ShiftAssignments
                    SET EmployeeId = ?, ModifiedAt = ?, ModifiedBy = ?
                    WHERE Id = ?
                """, (
                    requesting_employee_id,
                    datetime.utcnow().isoformat(),
                    session.get('user_email'),
                    shift_assignment_id
                ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            app.logger.error(f"Process shift exchange error: {str(e)}")
            return jsonify({'error': f'Fehler beim Bearbeiten: {str(e)}'}), 500
    
    # ============================================================================
    # STATISTICS ENDPOINTS
    # ============================================================================
    
    @app.route('/api/statistics/dashboard', methods=['GET'])
    def get_dashboard_stats():
        """Get dashboard statistics"""
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            # Default to current month
            today = date.today()
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Employee work hours
        cursor.execute("""
            SELECT e.Id, e.Vorname, e.Name, e.TeamId,
                   COUNT(sa.Id) as ShiftCount,
                   COUNT(sa.Id) * 8.0 as TotalHours
            FROM Employees e
            LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
                AND sa.Date >= ? AND sa.Date <= ?
            GROUP BY e.Id, e.Vorname, e.Name, e.TeamId
            HAVING ShiftCount > 0
            ORDER BY TotalHours DESC
        """, (start_date.isoformat(), end_date.isoformat()))
        
        employee_work_hours = []
        for row in cursor.fetchall():
            employee_work_hours.append({
                'employeeId': row['Id'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'shiftCount': row['ShiftCount'],
                'totalHours': row['TotalHours']
            })
        
        # Team shift distribution
        cursor.execute("""
            SELECT t.Id, t.Name,
                   st.Code,
                   COUNT(sa.Id) as ShiftCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
                AND sa.Date >= ? AND sa.Date <= ?
            LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            WHERE st.Code IS NOT NULL
            GROUP BY t.Id, t.Name, st.Code
            ORDER BY t.Name, st.Code
        """, (start_date.isoformat(), end_date.isoformat()))
        
        team_shift_data = {}
        for row in cursor.fetchall():
            team_id = row['Id']
            if team_id not in team_shift_data:
                team_shift_data[team_id] = {
                    'teamId': team_id,
                    'teamName': row['Name'],
                    'shiftCounts': {}
                }
            team_shift_data[team_id]['shiftCounts'][row['Code']] = row['ShiftCount']
        
        team_shift_distribution = list(team_shift_data.values())
        
        # Employee absence days
        cursor.execute("""
            SELECT e.Id, e.Vorname, e.Name,
                   SUM(julianday(a.EndDate) - julianday(a.StartDate) + 1) as TotalDays
            FROM Employees e
            JOIN Absences a ON e.Id = a.EmployeeId
            WHERE (a.StartDate <= ? AND a.EndDate >= ?)
               OR (a.StartDate >= ? AND a.StartDate <= ?)
            GROUP BY e.Id, e.Vorname, e.Name
            HAVING TotalDays > 0
            ORDER BY TotalDays DESC
        """, (end_date.isoformat(), start_date.isoformat(),
              start_date.isoformat(), end_date.isoformat()))
        
        employee_absence_days = []
        for row in cursor.fetchall():
            employee_absence_days.append({
                'employeeId': row['Id'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'totalDays': int(row['TotalDays'])
            })
        
        # Team workload
        cursor.execute("""
            SELECT t.Id, t.Name,
                   COUNT(DISTINCT e.Id) as EmployeeCount,
                   COUNT(sa.Id) as TotalShifts,
                   CASE WHEN COUNT(DISTINCT e.Id) > 0 
                        THEN CAST(COUNT(sa.Id) AS REAL) / COUNT(DISTINCT e.Id)
                        ELSE 0 END as AvgShiftsPerEmployee
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
                AND sa.Date >= ? AND sa.Date <= ?
            GROUP BY t.Id, t.Name
            HAVING EmployeeCount > 0
            ORDER BY t.Name
        """, (start_date.isoformat(), end_date.isoformat()))
        
        team_workload = []
        for row in cursor.fetchall():
            team_workload.append({
                'teamId': row['Id'],
                'teamName': row['Name'],
                'employeeCount': row['EmployeeCount'],
                'totalShifts': row['TotalShifts'],
                'averageShiftsPerEmployee': row['AvgShiftsPerEmployee']
            })
        
        conn.close()
        
        return jsonify({
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'employeeWorkHours': employee_work_hours,
            'teamShiftDistribution': team_shift_distribution,
            'employeeAbsenceDays': employee_absence_days,
            'teamWorkload': team_workload
        })
    
    # ============================================================================
    # AUDIT LOG ENDPOINTS
    # ============================================================================
    
    @app.route('/api/auditlogs', methods=['GET'])
    @require_role('Admin', 'Disponent')
    def get_audit_logs():
        """Get audit logs with pagination and filters"""
        try:
            # Get and validate pagination parameters
            try:
                page = int(request.args.get('page', 1))
                page_size = int(request.args.get('pageSize', 50))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid pagination parameters'}), 400
            
            # Validate pagination ranges
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = min(max(page_size, 1), 100)
            
            # Get filter parameters
            entity_name = request.args.get('entityName')
            action = request.args.get('action')
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Build WHERE clause with parameterized queries for safety
            where_clauses = []
            params = []
            
            # Whitelist valid filters to prevent any potential SQL injection
            if entity_name:
                where_clauses.append("EntityName = ?")
                params.append(entity_name)
            
            if action:
                where_clauses.append("Action = ?")
                params.append(action)
            
            if start_date:
                where_clauses.append("DATE(Timestamp) >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("DATE(Timestamp) <= ?")
                params.append(end_date)
            
            # Safe: only joining static WHERE clauses, all values are parameterized
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM AuditLogs WHERE {where_sql}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()['total']
            
            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            offset = (page - 1) * page_size
            
            # Get paginated results - safe: WHERE clause uses only parameterized queries
            select_query = f"""
                SELECT Id, Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes
                FROM AuditLogs
                WHERE {where_sql}
                ORDER BY Timestamp DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(select_query, params + [page_size, offset])
            
            items = []
            for row in cursor.fetchall():
                items.append({
                    'id': row['Id'],
                    'timestamp': row['Timestamp'],
                    'userId': row['UserId'],
                    'userName': row['UserName'],
                    'entityName': row['EntityName'],
                    'entityId': row['EntityId'],
                    'action': row['Action'],
                    'changes': row['Changes']
                })
            
            conn.close()
            
            return jsonify({
                'items': items,
                'page': page,
                'pageSize': page_size,
                'totalCount': total_count,
                'totalPages': total_pages,
                'hasPreviousPage': page > 1,
                'hasNextPage': page < total_pages
            })
            
        except Exception as e:
            app.logger.error(f"Get audit logs error: {str(e)}")
            return jsonify({'error': f'Fehler beim Laden der Audit-Logs: {str(e)}'}), 500
    
    @app.route('/api/auditlogs/recent/<int:count>', methods=['GET'])
    @require_role('Admin', 'Disponent')
    def get_recent_audit_logs(count):
        """Get recent audit logs (simplified endpoint for backwards compatibility)"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT Id, Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes
                FROM AuditLogs
                ORDER BY Timestamp DESC
                LIMIT ?
            """, (count,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row['Id'],
                    'timestamp': row['Timestamp'],
                    'userId': row['UserId'],
                    'userName': row['UserName'],
                    'entityName': row['EntityName'],
                    'entityId': row['EntityId'],
                    'action': row['Action'],
                    'changes': row['Changes']
                })
            
            conn.close()
            return jsonify(logs)
            
        except Exception as e:
            app.logger.error(f"Get recent audit logs error: {str(e)}")
            return jsonify({'error': f'Fehler beim Laden der Audit-Logs: {str(e)}'}), 500
    
    # ============================================================================
    # STATIC FILES (Web UI)
    # ============================================================================
    
    @app.route('/')
    def index():
        """Serve the main web UI"""
        return app.send_static_file('index.html')
    
    return app


if __name__ == "__main__":
    import os
    # Only enable debug in development (not in production)
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app = create_app()
    app.run(debug=debug_mode, port=5000)
