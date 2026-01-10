"""
Tests for automatic springer replacement feature.

Tests verify that:
1. Suitable springers are found considering legal requirements
2. Springers are automatically assigned when absence is reported
3. Notifications are sent to admins and springers
4. Rest time and consecutive day limits are respected
"""

from datetime import date, timedelta
import sqlite3
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(__file__))

from springer_replacement import (
    find_suitable_springer,
    assign_springer_to_shift,
    check_rest_time_compliance,
    check_consecutive_days_limit,
    process_absence_with_springer_assignment
)


def create_test_database():
    """Create a test database with sample data"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create necessary tables
    cursor.execute("""
        CREATE TABLE Employees (
            Id INTEGER PRIMARY KEY,
            Vorname TEXT,
            Name TEXT,
            Email TEXT,
            TeamId INTEGER,
            IsTdQualified INTEGER DEFAULT 0,
            IsBrandmeldetechniker INTEGER DEFAULT 0,
            IsBrandschutzbeauftragter INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Teams (
            Id INTEGER PRIMARY KEY,
            Name TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftTypes (
            Id INTEGER PRIMARY KEY,
            Code TEXT,
            Name TEXT,
            StartTime TEXT,
            EndTime TEXT,
            DurationHours REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftAssignments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER,
            ShiftTypeId INTEGER,
            Date TEXT,
            IsManual INTEGER DEFAULT 0,
            IsFixed INTEGER DEFAULT 0,
            Notes TEXT,
            CreatedAt TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Absences (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER,
            Type INTEGER,
            StartDate TEXT,
            EndDate TEXT,
            Notes TEXT,
            CreatedAt TEXT,
            CreatedBy TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE AdminNotifications (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Type TEXT,
            Severity TEXT,
            Title TEXT,
            Message TEXT,
            ShiftDate TEXT,
            ShiftCode TEXT,
            EmployeeId INTEGER,
            CreatedAt TEXT,
            IsRead INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE EmailSettings (
            Id INTEGER PRIMARY KEY,
            SmtpHost TEXT,
            SmtpPort INTEGER,
            UseSsl INTEGER,
            RequiresAuthentication INTEGER,
            Username TEXT,
            Password TEXT,
            SenderEmail TEXT,
            SenderName TEXT,
            ReplyToEmail TEXT,
            IsEnabled INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Users (
            Id INTEGER PRIMARY KEY,
            EmployeeId INTEGER,
            Role TEXT
        )
    """)
    
    # Insert test data
    # Teams
    cursor.execute("INSERT INTO Teams (Id, Name) VALUES (1, 'Team Alpha')")
    cursor.execute("INSERT INTO Teams (Id, Name) VALUES (2, 'Team Beta')")
    cursor.execute("INSERT INTO Teams (Id, Name) VALUES (3, 'Team Gamma')")
    
    # Employees
    employees = [
        (1, 'Max', 'Müller', 'max@example.com', 1),
        (2, 'Anna', 'Schmidt', 'anna@example.com', 1),
        (3, 'Peter', 'Weber', 'peter@example.com', 1),
        (4, 'Lisa', 'Meyer', 'lisa@example.com', 1),
        (5, 'Tom', 'Wagner', 'tom@example.com', 1),
        (6, 'Julia', 'Becker', 'julia@example.com', 2),
        (7, 'Michael', 'Schulz', 'michael@example.com', 2),
        (8, 'Sarah', 'Hoffmann', 'sarah@example.com', 2),
    ]
    for emp in employees:
        cursor.execute(
            "INSERT INTO Employees (Id, Vorname, Name, Email, TeamId) VALUES (?, ?, ?, ?, ?)",
            emp
        )
    
    # Shift types
    cursor.execute("INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours) VALUES (1, 'F', 'Frühdienst', '05:45', '13:45', 8.0)")
    cursor.execute("INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours) VALUES (2, 'S', 'Spätdienst', '13:45', '21:45', 8.0)")
    cursor.execute("INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours) VALUES (3, 'N', 'Nachtdienst', '21:45', '05:45', 8.0)")
    
    # Email settings (disabled for testing)
    cursor.execute("""
        INSERT INTO EmailSettings (
            Id, SmtpHost, SmtpPort, UseSsl, RequiresAuthentication,
            Username, Password, SenderEmail, SenderName, ReplyToEmail, IsEnabled
        ) VALUES (1, 'smtp.example.com', 587, 0, 0, '', '', 'test@example.com', 'Test', '', 0)
    """)
    
    conn.commit()
    return conn


def test_find_suitable_springer_same_team():
    """Test finding a springer from the same team"""
    print("\n" + "=" * 70)
    print("TEST 1: Find Suitable Springer - Same Team")
    print("=" * 70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Assign Max (ID 1) to early shift on 2026-01-10
    target_date = date(2026, 1, 10)
    cursor.execute("""
        INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
        VALUES (1, 1, ?, '2026-01-01')
    """, (target_date.isoformat(),))
    conn.commit()
    
    # Try to find springer for same shift (Max is absent)
    springer = find_suitable_springer(conn, target_date, 'F', 1)
    
    if springer:
        print(f"✓ Found springer: {springer['employeeName']}")
        print(f"  Same team: {springer['isSameTeam']}")
        print(f"  Email: {springer['email']}")
        assert springer['isSameTeam'], "Should prefer same team"
        assert springer['employeeId'] != 1, "Should not assign absent employee"
        return True
    else:
        print("❌ No springer found")
        return False


def test_find_springer_cross_team():
    """Test finding a springer from a different team"""
    print("\n" + "=" * 70)
    print("TEST 2: Find Suitable Springer - Cross Team")
    print("=" * 70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Assign all Team Alpha members except Max to shifts
    target_date = date(2026, 1, 10)
    for emp_id in [2, 3, 4, 5]:
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
            VALUES (?, 1, ?, '2026-01-01')
        """, (emp_id, target_date.isoformat()))
    conn.commit()
    
    # Try to find springer (should look at other teams)
    springer = find_suitable_springer(conn, target_date, 'F', 1)
    
    if springer:
        print(f"✓ Found cross-team springer: {springer['employeeName']}")
        print(f"  Team ID: {springer['teamId']}")
        print(f"  Same team: {springer['isSameTeam']}")
        assert not springer['isSameTeam'], "Should be from different team"
        assert springer['teamId'] != 1, "Should be from different team"
        return True
    else:
        print("❌ No cross-team springer found")
        return False


def test_rest_time_violation():
    """Test that rest time violations are detected"""
    print("\n" + "=" * 70)
    print("TEST 3: Rest Time Violation Detection")
    print("=" * 70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Assign employee 2 to late shift on day before
    previous_day = date(2026, 1, 9)
    cursor.execute("""
        INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
        VALUES (2, 2, ?, '2026-01-01')
    """, (previous_day.isoformat(),))
    conn.commit()
    
    # Check if early shift next day would violate rest time
    target_date = date(2026, 1, 10)
    compliant, reason = check_rest_time_compliance(conn, 2, target_date, 'F')
    
    if not compliant:
        print(f"✓ Rest time violation detected: {reason}")
        return True
    else:
        print("❌ Rest time violation not detected")
        return False


def test_consecutive_days_limit():
    """Test that consecutive days limit is enforced"""
    print("\n" + "=" * 70)
    print("TEST 4: Consecutive Days Limit")
    print("=" * 70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Assign employee 3 to shifts for 6 consecutive days
    start_date = date(2026, 1, 4)
    for i in range(6):
        shift_date = start_date + timedelta(days=i)
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
            VALUES (3, 1, ?, '2026-01-01')
        """, (shift_date.isoformat(),))
    conn.commit()
    
    # Check if adding 7th consecutive day would violate limit
    target_date = start_date + timedelta(days=6)
    compliant, reason = check_consecutive_days_limit(conn, 3, target_date)
    
    if not compliant:
        print(f"✓ Consecutive days limit detected: {reason}")
        return True
    else:
        print("❌ Consecutive days limit not detected")
        return False


def test_automatic_springer_assignment():
    """Test automatic springer assignment on absence"""
    print("\n" + "=" * 70)
    print("TEST 5: Automatic Springer Assignment")
    print("=" * 70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Create shifts for employee 1 for 3 days
    start_date = date(2026, 1, 10)
    for i in range(3):
        shift_date = start_date + timedelta(days=i)
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
            VALUES (1, 1, ?, '2026-01-01')
        """, (shift_date.isoformat(),))
    conn.commit()
    
    # Create absence for employee 1
    absence_id = 999
    end_date = start_date + timedelta(days=2)
    
    # Process absence with springer assignment
    results = process_absence_with_springer_assignment(
        conn, absence_id, 1, start_date, end_date, 1, 'test_user'
    )
    
    print(f"\nResults:")
    print(f"  Shifts needing coverage: {results['shiftsNeedingCoverage']}")
    print(f"  Assignments created: {results['assignmentsCreated']}")
    print(f"  Notifications sent: {results['notificationsSent']}")
    
    if results['assignmentsCreated'] > 0:
        print(f"\n✓ Successfully assigned {results['assignmentsCreated']} springer(s)")
        for detail in results['details']:
            if detail['status'] == 'assigned':
                print(f"  - {detail['date']}: {detail['springerName']} for {detail['shiftName']}")
        return True
    else:
        print("❌ No springers assigned")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("SPRINGER REPLACEMENT TESTS")
    print("=" * 70)
    
    tests = [
        ("Same Team Springer", test_find_suitable_springer_same_team),
        ("Cross Team Springer", test_find_springer_cross_team),
        ("Rest Time Violation", test_rest_time_violation),
        ("Consecutive Days Limit", test_consecutive_days_limit),
        ("Automatic Assignment", test_automatic_springer_assignment),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
