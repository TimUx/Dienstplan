"""
Flask Web API for shift planning system.
Provides REST API endpoints compatible with the existing .NET Web UI.
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import sqlite3
import json

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


def create_app(db_path: str = "dienstplan.db") -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Configured Flask app
    """
    app = Flask(__name__, static_folder='wwwroot', static_url_path='')
    CORS(app)  # Enable CORS for all routes
    
    db = Database(db_path)
    
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
    
    # ============================================================================
    # TEAM ENDPOINTS
    # ============================================================================
    
    @app.route('/api/teams', methods=['GET'])
    def get_teams():
        """Get all teams"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Teams ORDER BY Name")
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'id': row['Id'],
                'name': row['Name'],
                'description': row['Description'],
                'email': row['Email']
            })
        
        conn.close()
        return jsonify(teams)
    
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
