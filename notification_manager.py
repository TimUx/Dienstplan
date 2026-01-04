"""
Notification manager for tracking and alerting administrators about understaffing issues.

This module provides functions to:
- Check if minimum shift strength requirements are met
- Create notifications when understaffing is detected
- Manage notification lifecycle (create, read, dismiss)
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
import sqlite3


# Date format for German locale
DATE_FORMAT_DE = '%d.%m.%Y'


def get_staffing_requirements(conn: sqlite3.Connection) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Load staffing requirements from database.
    
    Returns:
        Dict with structure: {shift_code: {"weekday": {"min": x, "max": y}, "weekend": {"min": a, "max": b}}}
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Code, MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend
        FROM ShiftTypes
        WHERE IsActive = 1 AND Code IN ('F', 'S', 'N')
    """)
    
    staffing_reqs = {}
    for row in cursor.fetchall():
        code = row[0]
        staffing_reqs[code] = {
            "weekday": {"min": row[1], "max": row[2]},
            "weekend": {"min": row[3], "max": row[4]}
        }
    
    # Fallback to hardcoded values if database doesn't have the columns yet
    if not staffing_reqs:
        staffing_reqs = {
            "F": {"weekday": {"min": 4, "max": 5}, "weekend": {"min": 2, "max": 3}},
            "S": {"weekday": {"min": 3, "max": 4}, "weekend": {"min": 2, "max": 3}},
            "N": {"weekday": {"min": 3, "max": 3}, "weekend": {"min": 2, "max": 3}},
        }
    
    return staffing_reqs


def check_staffing_for_date(
    conn: sqlite3.Connection,
    check_date: date,
    shift_code: str
) -> Tuple[int, int, bool]:
    """
    Check if staffing requirements are met for a specific date and shift.
    
    Args:
        conn: Database connection
        check_date: Date to check
        shift_code: Shift code (F, S, N)
        
    Returns:
        Tuple of (required_staff, actual_staff, is_understaffed)
    """
    cursor = conn.cursor()
    
    # Get staffing requirements from database
    staffing_reqs = get_staffing_requirements(conn)
    
    if shift_code not in staffing_reqs:
        return (0, 0, False)
    
    # Determine requirements based on day of week
    is_weekend = check_date.weekday() >= 5
    day_type = "weekend" if is_weekend else "weekday"
    required_staff = staffing_reqs[shift_code][day_type]["min"]
    
    # Count actual staff assigned for this date and shift
    # Exclude employees who are absent on this date
    # Only count regular team members
    cursor.execute("""
        SELECT COUNT(DISTINCT sa.EmployeeId) as StaffCount
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        JOIN Employees e ON sa.EmployeeId = e.Id
        LEFT JOIN Absences a ON sa.EmployeeId = a.EmployeeId
            AND ? BETWEEN a.StartDate AND a.EndDate
        WHERE sa.Date = ?
          AND st.Code = ?
          AND a.Id IS NULL
    """, (check_date.isoformat(), check_date.isoformat(), shift_code))
    
    row = cursor.fetchone()
    actual_staff = row[0] if row else 0
    
    is_understaffed = actual_staff < required_staff
    
    return (required_staff, actual_staff, is_understaffed)


def check_absence_impact(
    conn: sqlite3.Connection,
    absence_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    absence_type: int
) -> List[Dict]:
    """
    Check if an absence creates understaffing situations.
    
    Args:
        conn: Database connection
        absence_id: ID of the absence
        employee_id: ID of the absent employee
        start_date: Absence start date
        end_date: Absence end date
        absence_type: Type of absence (1=Krank/AU, 2=Urlaub, 3=Lehrgang)
        
    Returns:
        List of understaffing issues found
    """
    cursor = conn.cursor()
    issues = []
    
    # Get employee info
    cursor.execute("""
        SELECT Vorname, Name, TeamId
        FROM Employees
        WHERE Id = ?
    """, (employee_id,))
    
    emp_row = cursor.fetchone()
    if not emp_row:
        return issues
    
    employee_name = f"{emp_row[0]} {emp_row[1]}"
    team_id = emp_row[2]
    
    # Get team name if applicable
    team_name = "Kein Team"
    if team_id:
        cursor.execute("SELECT Name FROM Teams WHERE Id = ?", (team_id,))
        team_row = cursor.fetchone()
        if team_row:
            team_name = team_row[0]
    
    # Map absence type to code
    absence_codes = {1: 'Krank / AU', 2: 'Urlaub', 3: 'Lehrgang'}
    absence_name = absence_codes.get(absence_type, 'Abwesenheit')
    
    # Check each date in the absence period
    current = start_date
    while current <= end_date:
        # Get shift assignments for this employee on this date
        cursor.execute("""
            SELECT st.Code, st.Name
            FROM ShiftAssignments sa
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            WHERE sa.EmployeeId = ?
              AND sa.Date = ?
              AND st.Code IN ('F', 'S', 'N')
        """, (employee_id, current.isoformat()))
        
        for shift_row in cursor.fetchall():
            shift_code = shift_row[0]
            shift_name = shift_row[1]
            
            # Check staffing after removing this employee
            required, actual, is_understaffed = check_staffing_for_date(conn, current, shift_code)
            
            # If removing this employee causes understaffing
            if is_understaffed:
                issues.append({
                    'date': current,
                    'shift_code': shift_code,
                    'shift_name': shift_name,
                    'employee_id': employee_id,
                    'employee_name': employee_name,
                    'team_id': team_id,
                    'team_name': team_name,
                    'absence_id': absence_id,
                    'absence_type': absence_name,
                    'required_staff': required,
                    'actual_staff': actual,
                    'deficit': required - actual
                })
        
        current += timedelta(days=1)
    
    return issues


def create_understaffing_notification(
    conn: sqlite3.Connection,
    issue: Dict,
    created_by: Optional[str] = None
) -> int:
    """
    Create an admin notification for an understaffing issue.
    
    Args:
        conn: Database connection
        issue: Dictionary with understaffing details
        created_by: Optional creator identifier
        
    Returns:
        ID of created notification
    """
    cursor = conn.cursor()
    
    # Determine severity based on deficit
    if issue['actual_staff'] == 0:
        severity = 'CRITICAL'
    elif issue['deficit'] >= 2:
        severity = 'HIGH'
    else:
        severity = 'WARNING'
    
    # Build notification message
    day_name = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'][issue['date'].weekday()]
    
    title = f"Mindestschichtstärke unterschritten: {issue['shift_name']} am {issue['date'].strftime(DATE_FORMAT_DE)}"
    
    message = (
        f"Die Mindestschichtstärke für die {issue['shift_name']} Schicht ({issue['shift_code']}) "
        f"am {day_name}, {issue['date'].strftime(DATE_FORMAT_DE)} wurde unterschritten.\n\n"
        f"Grund: {issue['absence_type']} von {issue['employee_name']} ({issue['team_name']})\n"
        f"Erforderlich: {issue['required_staff']} Mitarbeiter\n"
        f"Verfügbar: {issue['actual_staff']} Mitarbeiter\n"
        f"Fehlend: {issue['deficit']} Mitarbeiter"
    )
    
    cursor.execute("""
        INSERT INTO AdminNotifications (
            Type, Severity, Title, Message,
            ShiftDate, ShiftCode, TeamId, EmployeeId, AbsenceId,
            RequiredStaff, ActualStaff, CreatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        'UNDERSTAFFING',
        severity,
        title,
        message,
        issue['date'].isoformat(),
        issue['shift_code'],
        issue['team_id'],
        issue['employee_id'],
        issue['absence_id'],
        issue['required_staff'],
        issue['actual_staff']
    ))
    
    notification_id = cursor.lastrowid
    return notification_id


def process_absence_for_notifications(
    conn: sqlite3.Connection,
    absence_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    absence_type: int,
    created_by: Optional[str] = None
) -> List[int]:
    """
    Check an absence for staffing issues and create notifications.
    
    Args:
        conn: Database connection
        absence_id: ID of the absence
        employee_id: ID of the absent employee
        start_date: Absence start date
        end_date: Absence end date
        absence_type: Type of absence
        created_by: Optional creator identifier
        
    Returns:
        List of notification IDs created
    """
    # Check for understaffing issues
    issues = check_absence_impact(
        conn, absence_id, employee_id, start_date, end_date, absence_type
    )
    
    notification_ids = []
    
    # Create notifications for each issue
    for issue in issues:
        notification_id = create_understaffing_notification(conn, issue, created_by)
        notification_ids.append(notification_id)
    
    return notification_ids


def get_unread_notifications(conn: sqlite3.Connection, limit: int = 50) -> List[Dict]:
    """
    Get all unread admin notifications.
    
    Args:
        conn: Database connection
        limit: Maximum number of notifications to return
        
    Returns:
        List of notification dictionaries
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            n.Id, n.Type, n.Severity, n.Title, n.Message,
            n.ShiftDate, n.ShiftCode, n.RequiredStaff, n.ActualStaff,
            n.CreatedAt,
            e.Vorname, e.Name, 
            t.Name as TeamName
        FROM AdminNotifications n
        LEFT JOIN Employees e ON n.EmployeeId = e.Id
        LEFT JOIN Teams t ON n.TeamId = t.Id
        WHERE n.IsRead = 0
        ORDER BY n.CreatedAt DESC
        LIMIT ?
    """, (limit,))
    
    notifications = []
    for row in cursor.fetchall():
        notifications.append({
            'id': row[0],
            'type': row[1],
            'severity': row[2],
            'title': row[3],
            'message': row[4],
            'shiftDate': row[5],
            'shiftCode': row[6],
            'requiredStaff': row[7],
            'actualStaff': row[8],
            'createdAt': row[9],
            'employeeName': f"{row[10]} {row[11]}" if row[10] else None,
            'teamName': row[12],
            'isRead': False
        })
    
    return notifications


def mark_notification_as_read(
    conn: sqlite3.Connection,
    notification_id: int,
    read_by: Optional[str] = None
) -> bool:
    """
    Mark a notification as read.
    
    Args:
        conn: Database connection
        notification_id: ID of notification to mark as read
        read_by: Optional identifier of user marking as read
        
    Returns:
        True if successful, False otherwise
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE AdminNotifications
        SET IsRead = 1, ReadAt = CURRENT_TIMESTAMP, ReadBy = ?
        WHERE Id = ?
    """, (read_by, notification_id))
    
    conn.commit()
    return cursor.rowcount > 0


def get_notification_count(conn: sqlite3.Connection, unread_only: bool = True) -> int:
    """
    Get count of notifications.
    
    Args:
        conn: Database connection
        unread_only: If True, count only unread notifications
        
    Returns:
        Count of notifications
    """
    cursor = conn.cursor()
    
    if unread_only:
        cursor.execute("SELECT COUNT(*) FROM AdminNotifications WHERE IsRead = 0")
    else:
        cursor.execute("SELECT COUNT(*) FROM AdminNotifications")
    
    row = cursor.fetchone()
    return row[0] if row else 0
