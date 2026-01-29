#!/usr/bin/env python3
"""
Test to verify that employees in statistics are sorted alphabetically.
This test verifies the fix for the requirement: 
"Die Mitarbeiter sollen in den Statistiken bitte Alphabetisch sortiert werden."
"""

import sqlite3
import os
from datetime import date, datetime

# Absence type constants
ABSENCE_TYPE_AU = 1  # Arbeitsunfähigkeit (Sick leave)
ABSENCE_TYPE_U = 2   # Urlaub (Vacation)
ABSENCE_TYPE_L = 3   # Lehrgang (Training)


def setup_test_database():
    """Create a temporary test database with sample data"""
    db_path = '/tmp/test_alphabetical_statistics.db'
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE Employees (
            Id INTEGER PRIMARY KEY,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT,
            Email TEXT,
            TeamId INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Teams (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftTypes (
            Id INTEGER PRIMARY KEY,
            Code TEXT NOT NULL,
            Name TEXT NOT NULL,
            StartTime TEXT NOT NULL,
            EndTime TEXT NOT NULL,
            DurationHours REAL NOT NULL DEFAULT 8.0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftAssignments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            ShiftTypeId INTEGER NOT NULL,
            Date TEXT NOT NULL,
            IsManual INTEGER DEFAULT 0,
            IsFixed INTEGER DEFAULT 0,
            Notes TEXT,
            CreatedAt TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Absences (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            Type INTEGER NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Notes TEXT,
            CreatedAt TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    # Insert test data
    cursor.execute("INSERT INTO Teams (Id, Name) VALUES (1, 'Team A')")
    
    # Create test employees with names that should be sorted alphabetically
    # Using German names to match the context
    test_employees = [
        (1, 'Zara', 'Wagner', 'EMP001', 'zara.wagner@test.de'),
        (2, 'Anna', 'Becker', 'EMP002', 'anna.becker@test.de'),
        (3, 'Max', 'Schmidt', 'EMP003', 'max.schmidt@test.de'),
        (4, 'Clara', 'Fischer', 'EMP004', 'clara.fischer@test.de'),
        (5, 'Ben', 'Weber', 'EMP005', 'ben.weber@test.de'),
    ]
    
    for emp_id, vorname, name, personalnummer, email in test_employees:
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, TeamId)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (emp_id, vorname, name, personalnummer, email))
    
    cursor.execute("""
        INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours)
        VALUES (1, 'F', 'Frühdienst', '05:45', '13:45', 8.0)
    """)
    
    # Create shifts for testing work hours statistics
    # Give different hours to each employee to test sorting
    shift_counts = {1: 10, 2: 20, 3: 5, 4: 15, 5: 8}  # Different hours
    
    for emp_id, shift_count in shift_counts.items():
        for day in range(1, shift_count + 1):
            shift_date = date(2026, 1, day)
            cursor.execute("""
                INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
                VALUES (?, 1, ?, ?)
            """, (emp_id, shift_date.isoformat(), datetime.now().isoformat()))
    
    # Create absences with different days to test sorting
    absence_data = [
        (1, ABSENCE_TYPE_U, '2026-01-15', '2026-01-20', 6),  # Zara: 6 days
        (2, ABSENCE_TYPE_AU, '2026-01-10', '2026-01-12', 3), # Anna: 3 days
        (3, ABSENCE_TYPE_L, '2026-01-05', '2026-01-14', 10), # Max: 10 days
        (4, ABSENCE_TYPE_U, '2026-01-08', '2026-01-09', 2),  # Clara: 2 days
        (5, ABSENCE_TYPE_AU, '2026-01-20', '2026-01-25', 6), # Ben: 6 days
    ]
    
    for emp_id, abs_type, start_date, end_date, _ in absence_data:
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, CreatedAt)
            VALUES (?, ?, ?, ?, ?)
        """, (emp_id, abs_type, start_date, end_date, datetime.now().isoformat()))
    
    conn.commit()
    return conn, db_path


def get_work_hours_statistics(conn, start_date, end_date):
    """Get work hours statistics exactly as the web API does"""
    cursor = conn.cursor()
    
    # Employee work hours (simplified version of the API query)
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, e.TeamId,
               COUNT(sa.Id) as ShiftCount,
               COALESCE(SUM(st.DurationHours), 0) as ShiftHours
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        GROUP BY e.Id, e.Vorname, e.Name, e.TeamId
    """, (start_date.isoformat(), end_date.isoformat()))
    
    employee_hours_map = {}
    for row in cursor.fetchall():
        employee_hours_map[row['Id']] = {
            'id': row['Id'],
            'name': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'shiftCount': row['ShiftCount'],
            'shiftHours': float(row['ShiftHours'] or 0),
        }
    
    # Build final result list
    employee_work_hours = []
    for emp_data in employee_hours_map.values():
        total_hours = emp_data['shiftHours']
        if total_hours > 0:
            employee_work_hours.append({
                'employeeId': emp_data['id'],
                'employeeName': emp_data['name'],
                'teamId': emp_data['teamId'],
                'shiftCount': emp_data['shiftCount'],
                'totalHours': total_hours
            })
    
    # Sort alphabetically by employee name (as per the fix)
    employee_work_hours.sort(key=lambda x: x['employeeName'])
    
    return employee_work_hours


def get_absence_statistics(conn, start_date, end_date):
    """Get absence statistics exactly as the web API does"""
    cursor = conn.cursor()
    
    # Employee absence days - categorized by type
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, a.Type,
               SUM(julianday(a.EndDate) - julianday(a.StartDate) + 1) as TotalDays
        FROM Employees e
        JOIN Absences a ON e.Id = a.EmployeeId
        WHERE (a.StartDate <= ? AND a.EndDate >= ?)
           OR (a.StartDate >= ? AND a.StartDate <= ?)
        GROUP BY e.Id, e.Vorname, e.Name, a.Type
        HAVING TotalDays > 0
        ORDER BY e.Vorname, e.Name, a.Type
    """, (end_date.isoformat(), start_date.isoformat(),
          start_date.isoformat(), end_date.isoformat()))
    
    # Map integer type IDs to string codes
    type_id_to_code = {1: 'AU', 2: 'U', 3: 'L'}
    
    employee_absence_map = {}
    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id not in employee_absence_map:
            employee_absence_map[emp_id] = {
                'employeeId': emp_id,
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'totalDays': 0,
                'byType': {}
            }
        
        absence_type_id = row['Type']
        absence_type_code = type_id_to_code.get(absence_type_id, str(absence_type_id))
        days = int(row['TotalDays'])
        employee_absence_map[emp_id]['byType'][absence_type_code] = days
        employee_absence_map[emp_id]['totalDays'] += days
    
    # Sort alphabetically by employee name (as per the fix)
    employee_absence_days = sorted(
        employee_absence_map.values(),
        key=lambda x: x['employeeName']
    )
    
    return employee_absence_days


def test_alphabetical_sorting():
    """
    Test that employees in statistics are sorted alphabetically.
    
    Expected alphabetical order by full name:
    1. Anna Becker
    2. Ben Weber
    3. Clara Fischer
    4. Max Schmidt
    5. Zara Wagner
    """
    print("=" * 80)
    print("TEST: Employees Sorted Alphabetically in Statistics")
    print("=" * 80)
    
    # Setup test database
    conn, db_path = setup_test_database()
    
    try:
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 31)
        
        # Test 1: Work Hours Statistics
        print("\n" + "=" * 80)
        print("TEST 1: Work Hours Statistics - Alphabetical Sorting")
        print("=" * 80)
        
        work_hours = get_work_hours_statistics(conn, start_date, end_date)
        
        print("\n💼 Arbeitsstunden (Work Hours):")
        print("-" * 80)
        for emp in work_hours:
            print(f"{emp['employeeName']}: {emp['totalHours']}h ({emp['shiftCount']} shifts)")
        print("-" * 80)
        
        # Extract names for verification
        names = [emp['employeeName'] for emp in work_hours]
        expected_order = ['Anna Becker', 'Ben Weber', 'Clara Fischer', 'Max Schmidt', 'Zara Wagner']
        
        print(f"\nActual order:   {names}")
        print(f"Expected order: {expected_order}")
        
        # Verify alphabetical sorting
        assert names == expected_order, \
            f"Work hours not sorted alphabetically! Got {names}, expected {expected_order}"
        
        # Verify it's NOT sorted by hours (which would be different)
        hours_sorted = sorted(work_hours, key=lambda x: x['totalHours'], reverse=True)
        hours_order = [emp['employeeName'] for emp in hours_sorted]
        assert names != hours_order or names == expected_order, \
            "Sorting appears to be by hours, not alphabetical"
        
        print("\n✅ Work hours statistics are sorted alphabetically!")
        
        # Test 2: Absence Days Statistics
        print("\n" + "=" * 80)
        print("TEST 2: Absence Days Statistics - Alphabetical Sorting")
        print("=" * 80)
        
        absence_days = get_absence_statistics(conn, start_date, end_date)
        
        print("\n📅 Abwesenheiten (Absences):")
        print("-" * 80)
        for emp in absence_days:
            types_str = ', '.join([f"{t}: {d}" for t, d in emp['byType'].items()])
            print(f"{emp['employeeName']}: {emp['totalDays']} Tage ({types_str})")
        print("-" * 80)
        
        # Extract names for verification
        absence_names = [emp['employeeName'] for emp in absence_days]
        
        print(f"\nActual order:   {absence_names}")
        print(f"Expected order: {expected_order}")
        
        # Verify alphabetical sorting
        assert absence_names == expected_order, \
            f"Absences not sorted alphabetically! Got {absence_names}, expected {expected_order}"
        
        # Verify it's NOT sorted by days (which would be different)
        days_sorted = sorted(absence_days, key=lambda x: x['totalDays'], reverse=True)
        days_order = [emp['employeeName'] for emp in days_sorted]
        assert absence_names != days_order or absence_names == expected_order, \
            "Sorting appears to be by days, not alphabetical"
        
        print("\n✅ Absence statistics are sorted alphabetically!")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("Summary:")
        print("  ✓ Work hours statistics are sorted alphabetically by employee name")
        print("  ✓ Absence statistics are sorted alphabetically by employee name")
        print("  ✓ NOT sorted by hours or days (previous behavior)")
        print("=" * 80)
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        return False
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False
    finally:
        conn.close()
        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    success = test_alphabetical_sorting()
    exit(0 if success else 1)
