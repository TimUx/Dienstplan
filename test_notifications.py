"""
Test script for the notification system.

This script creates test data to verify that notifications are properly triggered
when minimum shift strength is violated.
"""

import sqlite3
from datetime import date, timedelta
from notification_manager import process_absence_for_notifications


def create_test_data(db_path='test_dienstplan.db'):
    """Create test employees, teams, and shift assignments"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test team
    cursor.execute("""
        INSERT INTO Teams (Name, Description, IsVirtual)
        VALUES ('Test Team Alpha', 'Test team for notifications', 0)
    """)
    team_id = cursor.lastrowid
    
    # Create test employees
    employees = []
    for i in range(5):
        cursor.execute("""
            INSERT INTO Employees (
                Vorname, Name, Personalnummer, Email, 
                PasswordHash, TeamId, IsActive
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            f'Test{i}',
            f'Employee{i}',
            f'TEST{i:04d}',
            f'test{i}@example.com',
            'test_hash',
            team_id
        ))
        employees.append(cursor.lastrowid)
    
    # Get shift type IDs
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'F'")
    frueh_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'S'")
    spaet_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'N'")
    nacht_id = cursor.fetchone()[0]
    
    # Create shift assignments for next week (weekday)
    test_date = date.today() + timedelta(days=7)
    # Make sure it's a weekday
    while test_date.weekday() >= 5:
        test_date += timedelta(days=1)
    
    # Assign 4 employees to Früh shift (minimum required for weekday)
    for i, emp_id in enumerate(employees[:4]):
        cursor.execute("""
            INSERT INTO ShiftAssignments (
                EmployeeId, ShiftTypeId, Date, IsManual, IsFixed,
                CreatedAt, CreatedBy
            )
            VALUES (?, ?, ?, 0, 0, CURRENT_TIMESTAMP, 'test_script')
        """, (emp_id, frueh_id, test_date.isoformat()))
    
    conn.commit()
    
    print(f"✓ Created test team (ID: {team_id})")
    print(f"✓ Created {len(employees)} test employees")
    print(f"✓ Created 4 shift assignments for {test_date.isoformat()} (Früh shift)")
    print(f"  Employees assigned: {employees[:4]}")
    
    return conn, team_id, employees, test_date


def test_notification_on_absence(db_path='test_dienstplan.db'):
    """Test that notification is created when absence causes understaffing"""
    
    print("\n" + "="*70)
    print("TESTING NOTIFICATION SYSTEM")
    print("="*70)
    
    # Create test data
    conn, team_id, employees, test_date = create_test_data(db_path)
    cursor = conn.cursor()
    
    # Check current staffing
    print(f"\n📊 Current staffing for {test_date.isoformat()}:")
    cursor.execute("""
        SELECT st.Code, COUNT(*) as Count
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.Date = ?
        GROUP BY st.Code
    """, (test_date.isoformat(),))
    
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} employees")
    
    # Create an absence that will cause understaffing
    # Remove one of the 4 employees (minimum is 4, so this will trigger alert)
    absent_employee_id = employees[0]
    
    print(f"\n⚠️  Creating absence for employee {absent_employee_id}...")
    print(f"   Date range: {test_date.isoformat()} to {test_date.isoformat()}")
    
    cursor.execute("""
        INSERT INTO Absences (
            EmployeeId, Type, StartDate, EndDate, Notes,
            CreatedAt, CreatedBy
        )
        VALUES (?, 2, ?, ?, 'Test absence for notification', CURRENT_TIMESTAMP, 'test_script')
    """, (absent_employee_id, test_date.isoformat(), test_date.isoformat()))
    
    absence_id = cursor.lastrowid
    conn.commit()
    
    print(f"   Absence ID: {absence_id}")
    
    # Process absence for notifications
    print(f"\n🔔 Processing absence for notifications...")
    notification_ids = process_absence_for_notifications(
        conn,
        absence_id,
        absent_employee_id,
        test_date,
        test_date,
        2,  # Type 2 = Urlaub
        'test_script'
    )
    
    conn.commit()
    
    if notification_ids:
        print(f"✓ Created {len(notification_ids)} notification(s)")
        
        # Display notifications
        print(f"\n📬 Notification Details:")
        for notif_id in notification_ids:
            cursor.execute("""
                SELECT Type, Severity, Title, Message, ShiftDate, ShiftCode,
                       RequiredStaff, ActualStaff, CreatedAt
                FROM AdminNotifications
                WHERE Id = ?
            """, (notif_id,))
            
            notif = cursor.fetchone()
            if notif:
                print(f"\n   ID: {notif_id}")
                print(f"   Type: {notif[0]}")
                print(f"   Severity: {notif[1]}")
                print(f"   Title: {notif[2]}")
                print(f"   Message:")
                for line in notif[3].split('\n'):
                    print(f"      {line}")
                print(f"   Shift Date: {notif[4]}")
                print(f"   Shift Code: {notif[5]}")
                print(f"   Required: {notif[6]}, Actual: {notif[7]}")
    else:
        print("⚠️  No notifications created!")
        print("   This might mean staffing is still adequate or no shifts were affected.")
    
    # Show final staffing after absence
    print(f"\n📊 Final staffing for {test_date.isoformat()} (after absence):")
    cursor.execute("""
        SELECT st.Code, COUNT(*) as Count
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.Date = ?
          AND sa.EmployeeId != ?
        GROUP BY st.Code
    """, (test_date.isoformat(), absent_employee_id))
    
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} employees (minimum required: 4 for weekday)")
    
    conn.close()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_notification_on_absence()
