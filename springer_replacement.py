"""
Automatic springer (replacement employee) assignment module.

This module provides functionality to automatically assign replacement employees
when an absence is reported, considering:
- Legal requirements (rest times, consecutive work days)
- Employee qualifications
- Team availability and cross-team springer capability
- Shift staffing requirements

Key features:
- Find suitable replacement employees from any team
- Respect rest time regulations (11 hours minimum)
- Consider consecutive work day limits
- Automatic assignment on absence report
- Notifications to admins and assigned springer
"""

from datetime import date, timedelta, datetime
from typing import List, Dict, Optional, Tuple
import sqlite3
from entities import Employee, ShiftType, Absence
from email_service import send_email


# Rest time requirement: minimum 11 hours between shifts
MINIMUM_REST_HOURS = 11

# Maximum consecutive working days
MAXIMUM_CONSECUTIVE_DAYS = 6


def get_employee_shift_on_date(
    conn: sqlite3.Connection,
    employee_id: int,
    check_date: date
) -> Optional[Dict]:
    """
    Get shift assignment for an employee on a specific date.
    
    Args:
        conn: Database connection
        employee_id: Employee ID
        check_date: Date to check
        
    Returns:
        Dictionary with shift details or None if no assignment
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sa.Id, st.Code, st.StartTime, st.EndTime, st.DurationHours
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.EmployeeId = ? AND sa.Date = ?
    """, (employee_id, check_date.isoformat()))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        'assignmentId': row[0],
        'shiftCode': row[1],
        'startTime': row[2],
        'endTime': row[3],
        'duration': row[4]
    }


def check_rest_time_compliance(
    conn: sqlite3.Connection,
    employee_id: int,
    target_date: date,
    target_shift_code: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if assigning an employee to a shift would violate rest time requirements.
    
    Args:
        conn: Database connection
        employee_id: Employee ID to check
        target_date: Date of proposed shift
        target_shift_code: Shift code (F, S, N) for proposed assignment
        
    Returns:
        Tuple of (is_compliant: bool, reason: str)
    """
    cursor = conn.cursor()
    
    # Get target shift times
    cursor.execute("""
        SELECT StartTime, EndTime
        FROM ShiftTypes
        WHERE Code = ?
    """, (target_shift_code,))
    
    shift_row = cursor.fetchone()
    if not shift_row:
        return False, f"Schicht {target_shift_code} nicht gefunden"
    
    target_start = shift_row[0]
    target_end = shift_row[1]
    
    # Check shift on previous day
    previous_day = target_date - timedelta(days=1)
    prev_shift = get_employee_shift_on_date(conn, employee_id, previous_day)
    
    if prev_shift:
        # Check if rest time is sufficient
        # Simplified: Check for forbidden transitions (Spät -> Früh, Nacht -> Früh)
        forbidden_transitions = {
            'S': ['F'],  # Late shift -> Early shift (only 8 hours rest)
            'N': ['F'],  # Night shift -> Early shift (0 hours rest)
        }
        
        if prev_shift['shiftCode'] in forbidden_transitions:
            if target_shift_code in forbidden_transitions[prev_shift['shiftCode']]:
                return False, f"Ruhezeit-Verstoß: {prev_shift['shiftCode']} -> {target_shift_code} (min. 11h Ruhezeit erforderlich)"
    
    # Check shift on next day
    next_day = target_date + timedelta(days=1)
    next_shift = get_employee_shift_on_date(conn, employee_id, next_day)
    
    if next_shift:
        # Check forbidden transitions in forward direction
        forbidden_transitions = {
            'S': ['F'],
            'N': ['F'],
        }
        
        if target_shift_code in forbidden_transitions:
            if next_shift['shiftCode'] in forbidden_transitions[target_shift_code]:
                return False, f"Ruhezeit-Verstoß: {target_shift_code} -> {next_shift['shiftCode']} (min. 11h Ruhezeit erforderlich)"
    
    return True, None


def check_consecutive_days_limit(
    conn: sqlite3.Connection,
    employee_id: int,
    target_date: date
) -> Tuple[bool, Optional[str]]:
    """
    Check if assigning an employee would exceed consecutive working days limit.
    
    Args:
        conn: Database connection
        employee_id: Employee ID to check
        target_date: Date of proposed shift
        
    Returns:
        Tuple of (is_compliant: bool, reason: str)
    """
    cursor = conn.cursor()
    
    # Count consecutive days before target date
    days_before = 0
    check_date = target_date - timedelta(days=1)
    
    for i in range(MAXIMUM_CONSECUTIVE_DAYS):
        shift = get_employee_shift_on_date(conn, employee_id, check_date)
        if not shift:
            break
        days_before += 1
        check_date -= timedelta(days=1)
    
    # Count consecutive days after target date
    days_after = 0
    check_date = target_date + timedelta(days=1)
    
    for i in range(MAXIMUM_CONSECUTIVE_DAYS):
        shift = get_employee_shift_on_date(conn, employee_id, check_date)
        if not shift:
            break
        days_after += 1
        check_date += timedelta(days=1)
    
    total_consecutive = days_before + 1 + days_after  # +1 for target date
    
    if total_consecutive > MAXIMUM_CONSECUTIVE_DAYS:
        return False, f"Überschreitung max. aufeinanderfolgender Arbeitstage: {total_consecutive} > {MAXIMUM_CONSECUTIVE_DAYS}"
    
    return True, None


def is_employee_absent(
    conn: sqlite3.Connection,
    employee_id: int,
    check_date: date
) -> bool:
    """
    Check if an employee is absent on a specific date.
    
    Args:
        conn: Database connection
        employee_id: Employee ID
        check_date: Date to check
        
    Returns:
        True if employee is absent, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM Absences
        WHERE EmployeeId = ?
          AND ? BETWEEN StartDate AND EndDate
    """, (employee_id, check_date.isoformat()))
    
    row = cursor.fetchone()
    return row[0] > 0 if row else False


def find_suitable_springer(
    conn: sqlite3.Connection,
    absence_date: date,
    shift_code: str,
    absent_employee_id: int
) -> Optional[Dict]:
    """
    Find a suitable springer (replacement employee) for a specific shift.
    
    Selection criteria:
    1. Employee's team must be assigned to the shift type (NEW REQUIREMENT)
    2. Not already assigned on this date
    3. Not absent on this date
    4. Respects rest time requirements (11h minimum)
    5. Does not exceed consecutive days limit (max 6 days)
    6. Has appropriate qualifications (if needed)
    7. Preference: from same team, then other teams
    
    Example:
    - Employee from Team A (Early shift) is absent
    - Candidate from Team B: Team B is assigned to F, S, N shifts → ✅ Suitable
    - Candidate from Team F: Team F is NOT assigned to F shift → ❌ Not suitable
    
    Args:
        conn: Database connection
        absence_date: Date needing coverage
        shift_code: Shift code (F, S, N) needing coverage
        absent_employee_id: ID of absent employee (to get team info)
        
    Returns:
        Dictionary with springer details or None if no suitable employee found
    """
    cursor = conn.cursor()
    
    # Get absent employee's team
    cursor.execute("""
        SELECT TeamId
        FROM Employees
        WHERE Id = ?
    """, (absent_employee_id,))
    
    absent_emp_row = cursor.fetchone()
    absent_team_id = absent_emp_row[0] if absent_emp_row else None
    
    # Get shift type ID for the shift code
    cursor.execute("""
        SELECT Id
        FROM ShiftTypes
        WHERE Code = ?
    """, (shift_code,))
    
    shift_type_row = cursor.fetchone()
    if not shift_type_row:
        return None  # Shift type not found
    
    shift_type_id = shift_type_row[0]
    
    # Get all employees whose teams are assigned to this shift type
    # This is the NEW requirement: springer must be from a team assigned to the shift
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, e.TeamId, e.Email,
               e.IsTdQualified, e.IsBrandmeldetechniker, e.IsBrandschutzbeauftragter
        FROM Employees e
        INNER JOIN TeamShiftAssignments tsa ON e.TeamId = tsa.TeamId
        WHERE e.TeamId IS NOT NULL
          AND e.Id != ?
          AND tsa.ShiftTypeId = ?
        ORDER BY 
            CASE WHEN e.TeamId = ? THEN 0 ELSE 1 END,  -- Prefer same team
            e.Id
    """, (absent_employee_id, shift_type_id, absent_team_id))
    
    candidates = cursor.fetchall()
    
    for candidate in candidates:
        emp_id = candidate[0]
        emp_name = f"{candidate[1]} {candidate[2]}"
        emp_team_id = candidate[3]
        emp_email = candidate[4]
        
        # Check if already assigned on this date
        existing_shift = get_employee_shift_on_date(conn, emp_id, absence_date)
        if existing_shift:
            continue  # Already working
        
        # Check if absent
        if is_employee_absent(conn, emp_id, absence_date):
            continue  # Employee is absent
        
        # Check rest time compliance
        rest_compliant, rest_reason = check_rest_time_compliance(
            conn, emp_id, absence_date, shift_code
        )
        if not rest_compliant:
            continue  # Rest time violation
        
        # Check consecutive days limit
        consecutive_ok, consec_reason = check_consecutive_days_limit(
            conn, emp_id, absence_date
        )
        if not consecutive_ok:
            continue  # Too many consecutive days
        
        # Found a suitable springer!
        return {
            'employeeId': emp_id,
            'employeeName': emp_name,
            'teamId': emp_team_id,
            'email': emp_email,
            'isSameTeam': emp_team_id == absent_team_id
        }
    
    return None  # No suitable springer found


def assign_springer_to_shift(
    conn: sqlite3.Connection,
    springer_id: int,
    shift_date: date,
    shift_code: str,
    absence_id: int,
    created_by: Optional[str] = None
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Assign a springer to a shift to cover an absence.
    
    Args:
        conn: Database connection
        springer_id: Employee ID to assign as springer
        shift_date: Date of shift
        shift_code: Shift code (F, S, N)
        absence_id: ID of absence being covered
        created_by: Optional creator identifier
        
    Returns:
        Tuple of (success: bool, assignment_id: int, error_message: str)
    """
    cursor = conn.cursor()
    
    # Get shift type ID for this code
    cursor.execute("""
        SELECT Id
        FROM ShiftTypes
        WHERE Code = ?
    """, (shift_code,))
    
    shift_row = cursor.fetchone()
    if not shift_row:
        return False, None, f"Schichttyp {shift_code} nicht gefunden"
    
    shift_type_id = shift_row[0]
    
    try:
        # Create shift assignment
        cursor.execute("""
            INSERT INTO ShiftAssignments (
                EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, Notes, CreatedAt
            )
            VALUES (?, ?, ?, 1, 0, ?, CURRENT_TIMESTAMP)
        """, (
            springer_id,
            shift_type_id,
            shift_date.isoformat(),
            f"Automatisch zugewiesen als Springer (Abwesenheit ID: {absence_id})"
        ))
        
        assignment_id = cursor.lastrowid
        conn.commit()
        
        return True, assignment_id, None
        
    except sqlite3.Error as e:
        conn.rollback()
        return False, None, f"Datenbankfehler: {str(e)}"


def process_absence_with_springer_assignment(
    conn: sqlite3.Connection,
    absence_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    absence_type: int,
    created_by: Optional[str] = None
) -> Dict:
    """
    Process an absence and automatically assign springers where needed.
    
    This function:
    1. Finds all shifts affected by the absence
    2. For each affected shift, tries to find a suitable springer
    3. Assigns springers automatically
    4. Creates notifications for admins and springers
    
    Args:
        conn: Database connection
        absence_id: ID of the absence
        employee_id: ID of absent employee
        start_date: Absence start date
        end_date: Absence end date
        absence_type: Type of absence
        created_by: Optional creator identifier
        
    Returns:
        Dictionary with results:
        {
            'assignmentsCreated': int,
            'notificationsSent': int,
            'shiftsNeedingCoverage': int,
            'details': List[Dict]
        }
    """
    cursor = conn.cursor()
    
    results = {
        'assignmentsCreated': 0,
        'notificationsSent': 0,
        'shiftsNeedingCoverage': 0,
        'details': []
    }
    
    # Get all shifts assigned to the absent employee in the date range
    cursor.execute("""
        SELECT sa.Id, sa.Date, st.Code, st.Name
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.EmployeeId = ?
          AND sa.Date BETWEEN ? AND ?
          AND st.Code IN ('F', 'S', 'N')
        ORDER BY sa.Date
    """, (employee_id, start_date.isoformat(), end_date.isoformat()))
    
    affected_shifts = cursor.fetchall()
    results['shiftsNeedingCoverage'] = len(affected_shifts)
    
    for shift_row in affected_shifts:
        assignment_id = shift_row[0]
        shift_date = date.fromisoformat(shift_row[1])
        shift_code = shift_row[2]
        shift_name = shift_row[3]
        
        # Try to find a suitable springer
        springer = find_suitable_springer(conn, shift_date, shift_code, employee_id)
        
        if springer:
            # Assign springer
            success, new_assignment_id, error = assign_springer_to_shift(
                conn, springer['employeeId'], shift_date, shift_code, absence_id, created_by
            )
            
            if success:
                results['assignmentsCreated'] += 1
                
                # Get absent employee name and absence type for notifications
                cursor.execute("SELECT Vorname, Name FROM Employees WHERE Id = ?", (employee_id,))
                absent_row = cursor.fetchone()
                absent_name = f"{absent_row[0]} {absent_row[1]}" if absent_row else "Unbekannt"
                
                absence_type_names = {1: 'Krank / AU', 2: 'Urlaub', 3: 'Lehrgang'}
                absence_type_name = absence_type_names.get(absence_type, 'Abwesenheit')
                
                # Send notification email to springer
                if springer['email']:
                    email_success, email_error = send_springer_notification_email(
                        conn,
                        springer['employeeId'],
                        springer['email'],
                        springer['employeeName'],
                        shift_date,
                        shift_name,
                        absent_name,
                        absence_type_name
                    )
                    if email_success:
                        results['notificationsSent'] += 1
                
                # Create in-app notification
                try:
                    create_springer_notification(
                        conn,
                        springer['employeeId'],
                        shift_date,
                        shift_code,
                        employee_id,
                        new_assignment_id
                    )
                except Exception as e:
                    # Log but don't fail if notification creation fails
                    print(f"Warning: Could not create in-app notification: {e}")
                
                # Send notification to admins
                try:
                    send_admin_springer_notification(
                        conn,
                        springer['employeeName'],
                        shift_date,
                        shift_name,
                        absent_name,
                        absence_type_name
                    )
                except Exception as e:
                    # Log but don't fail if admin notification fails
                    print(f"Warning: Could not send admin notification: {e}")
                
                results['details'].append({
                    'date': shift_date.isoformat(),
                    'shiftCode': shift_code,
                    'shiftName': shift_name,
                    'springerName': springer['employeeName'],
                    'springerId': springer['employeeId'],
                    'springerEmail': springer['email'],
                    'isSameTeam': springer['isSameTeam'],
                    'assignmentId': new_assignment_id,
                    'status': 'assigned'
                })
            else:
                results['details'].append({
                    'date': shift_date.isoformat(),
                    'shiftCode': shift_code,
                    'shiftName': shift_name,
                    'status': 'failed',
                    'error': error
                })
        else:
            # No springer found
            results['details'].append({
                'date': shift_date.isoformat(),
                'shiftCode': shift_code,
                'shiftName': shift_name,
                'status': 'no_springer_found'
            })
    
    return results


def send_springer_notification_email(
    conn: sqlite3.Connection,
    springer_id: int,
    springer_email: str,
    springer_name: str,
    shift_date: date,
    shift_name: str,
    absent_employee_name: str,
    absence_type_name: str
) -> Tuple[bool, str]:
    """
    Send email notification to springer about their assignment.
    
    Args:
        conn: Database connection
        springer_id: ID of springer employee
        springer_email: Email address of springer
        springer_name: Name of springer
        shift_date: Date of shift assignment
        shift_name: Name of shift
        absent_employee_name: Name of absent employee
        absence_type_name: Type of absence (Krank, Urlaub, etc.)
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    day_name = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'][shift_date.weekday()]
    date_formatted = shift_date.strftime('%d.%m.%Y')
    
    subject = f"Dienstplan - Automatische Springer-Zuweisung für {day_name}, {date_formatted}"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #FF9800; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .info-box {{ background-color: #fff; padding: 15px; border-left: 4px solid #FF9800; margin: 15px 0; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; 
                      font-size: 12px; color: #666; text-align: center; }}
            .important {{ color: #FF5722; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 Springer-Zuweisung</h1>
            </div>
            <div class="content">
                <p>Hallo {springer_name},</p>
                <p><strong>Sie wurden automatisch als Springer für eine Schicht eingeteilt.</strong></p>
                
                <div class="info-box">
                    <h3>Schicht-Details:</h3>
                    <p><strong>Datum:</strong> {day_name}, {date_formatted}</p>
                    <p><strong>Schicht:</strong> {shift_name}</p>
                    <p><strong>Grund:</strong> {absence_type_name} von {absent_employee_name}</p>
                </div>
                
                <p>Diese Zuweisung wurde automatisch vorgenommen, da ein Mitarbeiter kurzfristig ausgefallen ist.</p>
                
                <p class="important">Bitte überprüfen Sie die Zuweisung in der Dienstplan-App und melden Sie sich bei Problemen umgehend bei der Dienstplanung.</p>
                
                <p>Bei Fragen wenden Sie sich bitte an Ihren Administrator.</p>
            </div>
            <div class="footer">
                <p>Diese E-Mail wurde automatisch generiert.</p>
                <p>&copy; {datetime.now().year} Fritz Winter Eisengießerei GmbH & Co. KG</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
Hallo {springer_name},

Sie wurden automatisch als Springer für eine Schicht eingeteilt.

Schicht-Details:
- Datum: {day_name}, {date_formatted}
- Schicht: {shift_name}
- Grund: {absence_type_name} von {absent_employee_name}

Diese Zuweisung wurde automatisch vorgenommen, da ein Mitarbeiter kurzfristig ausgefallen ist.

Bitte überprüfen Sie die Zuweisung in der Dienstplan-App und melden Sie sich bei Problemen umgehend bei der Dienstplanung.

Bei Fragen wenden Sie sich bitte an Ihren Administrator.
    """
    
    if not springer_email:
        return False, "Keine E-Mail-Adresse für Springer vorhanden"
    
    return send_email(conn, springer_email, subject, body_html, body_text)


def create_springer_notification(
    conn: sqlite3.Connection,
    springer_id: int,
    shift_date: date,
    shift_code: str,
    absent_employee_id: int,
    assignment_id: int
) -> int:
    """
    Create an in-app notification for springer assignment.
    
    Args:
        conn: Database connection
        springer_id: ID of springer employee
        shift_date: Date of shift
        shift_code: Shift code
        absent_employee_id: ID of absent employee
        assignment_id: ID of new shift assignment
        
    Returns:
        ID of created notification
    """
    cursor = conn.cursor()
    
    # Get employee names
    cursor.execute("SELECT Vorname, Name FROM Employees WHERE Id = ?", (springer_id,))
    springer_row = cursor.fetchone()
    springer_name = f"{springer_row[0]} {springer_row[1]}" if springer_row else "Unbekannt"
    
    cursor.execute("SELECT Vorname, Name FROM Employees WHERE Id = ?", (absent_employee_id,))
    absent_row = cursor.fetchone()
    absent_name = f"{absent_row[0]} {absent_row[1]}" if absent_row else "Unbekannt"
    
    # Get shift name
    cursor.execute("SELECT Name FROM ShiftTypes WHERE Code = ?", (shift_code,))
    shift_row = cursor.fetchone()
    shift_name = shift_row[0] if shift_row else shift_code
    
    day_name = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'][shift_date.weekday()]
    date_formatted = shift_date.strftime('%d.%m.%Y')
    
    title = f"Springer-Zuweisung: {shift_name} am {date_formatted}"
    message = f"Sie wurden automatisch als Springer für die {shift_name} Schicht am {day_name}, {date_formatted} eingeteilt (Vertretung für {absent_name})."
    
    # Create notification (insert into a suitable notifications table)
    # Note: This assumes there's an EmployeeNotifications table - adjust as needed
    cursor.execute("""
        INSERT INTO AdminNotifications (
            Type, Severity, Title, Message,
            ShiftDate, ShiftCode, EmployeeId, CreatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        'SPRINGER_ASSIGNMENT',
        'INFO',
        title,
        message,
        shift_date.isoformat(),
        shift_code,
        springer_id
    ))
    
    notification_id = cursor.lastrowid
    conn.commit()
    
    return notification_id


def send_admin_springer_notification(
    conn: sqlite3.Connection,
    springer_name: str,
    shift_date: date,
    shift_name: str,
    absent_employee_name: str,
    absence_type_name: str
) -> Tuple[bool, str]:
    """
    Send notification to admins about automatic springer assignment.
    
    Args:
        conn: Database connection
        springer_name: Name of springer
        shift_date: Date of shift
        shift_name: Name of shift
        absent_employee_name: Name of absent employee
        absence_type_name: Type of absence
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    cursor = conn.cursor()
    
    # Get admin emails
    cursor.execute("""
        SELECT DISTINCT e.Email
        FROM Employees e
        JOIN Users u ON e.Id = u.EmployeeId
        WHERE u.Role IN ('Admin', 'Disponent')
          AND e.Email IS NOT NULL
          AND e.Email != ''
    """)
    
    admin_emails = [row[0] for row in cursor.fetchall()]
    
    if not admin_emails:
        return False, "Keine Admin-E-Mail-Adressen gefunden"
    
    day_name = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'][shift_date.weekday()]
    date_formatted = shift_date.strftime('%d.%m.%Y')
    
    subject = f"Dienstplan - Automatische Springer-Zuweisung: {springer_name}"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .info-box {{ background-color: #fff; padding: 15px; border-left: 4px solid #4CAF50; margin: 15px 0; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; 
                      font-size: 12px; color: #666; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Automatische Springer-Zuweisung</h1>
            </div>
            <div class="content">
                <p>Eine Springer-Zuweisung wurde automatisch vorgenommen:</p>
                
                <div class="info-box">
                    <h3>Details:</h3>
                    <p><strong>Springer:</strong> {springer_name}</p>
                    <p><strong>Datum:</strong> {day_name}, {date_formatted}</p>
                    <p><strong>Schicht:</strong> {shift_name}</p>
                    <p><strong>Ersetzt:</strong> {absent_employee_name} ({absence_type_name})</p>
                </div>
                
                <p>Der zugewiesene Mitarbeiter wurde per E-Mail benachrichtigt.</p>
                
                <p>Bitte überprüfen Sie die Zuweisung bei Bedarf in der Dienstplan-Anwendung.</p>
            </div>
            <div class="footer">
                <p>Diese E-Mail wurde automatisch generiert.</p>
                <p>&copy; {datetime.now().year} Fritz Winter Eisengießerei GmbH & Co. KG</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
Eine Springer-Zuweisung wurde automatisch vorgenommen:

Details:
- Springer: {springer_name}
- Datum: {day_name}, {date_formatted}
- Schicht: {shift_name}
- Ersetzt: {absent_employee_name} ({absence_type_name})

Der zugewiesene Mitarbeiter wurde per E-Mail benachrichtigt.

Bitte überprüfen Sie die Zuweisung bei Bedarf in der Dienstplan-Anwendung.
    """
    
    # Send to all admins
    success_count = 0
    errors = []
    
    for admin_email in admin_emails:
        success, error = send_email(conn, admin_email, subject, body_html, body_text)
        if success:
            success_count += 1
        else:
            errors.append(f"{admin_email}: {error}")
    
    if success_count > 0:
        return True, f"{success_count} Admin(s) benachrichtigt"
    else:
        return False, "; ".join(errors)
