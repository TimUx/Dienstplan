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
            
            # Auto-set BMT/BSB flags based on Funktion
            is_bmt = 1 if funktion == 'Brandmeldetechniker' else 0
            is_bsb = 1 if funktion == 'Brandschutzbeauftragter' else 0
            
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
                 IsSpringer, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, TeamId)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data.get('teamId')
            ))
            
            employee_id = cursor.lastrowid
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
            
            # Auto-set BMT/BSB flags based on Funktion
            is_bmt = 1 if funktion == 'Brandmeldetechniker' else 0
            is_bsb = 1 if funktion == 'Brandschutzbeauftragter' else 0
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if employee exists
            cursor.execute("SELECT Id FROM Employees WHERE Id = ?", (id,))
            if not cursor.fetchone():
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
                    IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?, TeamId = ?
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
                data.get('teamId'),
                id
            ))
            
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
            
            # Check if employee exists
            cursor.execute("SELECT Id FROM Employees WHERE Id = ?", (id,))
            if not cursor.fetchone():
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
            SELECT t.Id, t.Name, t.Description, t.Email,
                   COUNT(e.Id) as EmployeeCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            GROUP BY t.Id, t.Name, t.Description, t.Email
            ORDER BY t.Name
        """)
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'id': row['Id'],
                'name': row['Name'],
                'description': row['Description'],
                'email': row['Email'],
                'employeeCount': row['EmployeeCount']
            })
        
        conn.close()
        return jsonify(teams)
    
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
                INSERT INTO Teams (Name, Description, Email)
                VALUES (?, ?, ?)
            """, (
                data.get('name'),
                data.get('description'),
                data.get('email')
            ))
            
            team_id = cursor.lastrowid
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
            
            # Check if team exists
            cursor.execute("SELECT Id FROM Teams WHERE Id = ?", (id,))
            if not cursor.fetchone():
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
            
            # Check if team exists
            cursor.execute("SELECT Id FROM Teams WHERE Id = ?", (id,))
            if not cursor.fetchone():
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
            
            # Get absences
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
                employees, start_date, end_date, absences
            )
            
            # Solve
            result = solve_shift_planning(planning_model, time_limit_seconds=300)
            
            if not result:
                return jsonify({'error': 'No solution found'}), 500
            
            assignments, special_functions = result
            
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
        
        conn.close()
        return jsonify(absences)
    
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
        
        # Employee hours
        cursor.execute("""
            SELECT e.Id, e.Vorname, e.Name, e.TeamId,
                   COUNT(sa.Id) as ShiftCount
            FROM Employees e
            LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
                AND sa.Date >= ? AND sa.Date <= ?
            GROUP BY e.Id, e.Vorname, e.Name, e.TeamId
            ORDER BY e.Name, e.Vorname
        """, (start_date.isoformat(), end_date.isoformat()))
        
        employee_hours = []
        for row in cursor.fetchall():
            employee_hours.append({
                'employeeId': row['Id'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'shiftCount': row['ShiftCount'],
                'hours': row['ShiftCount'] * 8  # Approximate
            })
        
        conn.close()
        
        return jsonify({
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'employeeHours': employee_hours
        })
    
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
