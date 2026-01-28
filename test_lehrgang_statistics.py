#!/usr/bin/env python3
"""
Unit test to verify that absences are handled correctly for statistics:
- AU (sick leave): Remove shifts, do NOT count hours
- U (vacation): Remove shifts, do NOT count hours  
- L (Lehrgang/training): Remove shifts, BUT count 8h per training day
"""

import sqlite3
import os
from datetime import date, datetime, timezone
from entities import AbsenceType

# Absence type constants - MUST match database schema
# Database stores Type as INTEGER (not string!)
ABSENCE_TYPE_AU = 1  # Arbeitsunfähigkeit (Sick leave)
ABSENCE_TYPE_U = 2   # Urlaub (Vacation)
ABSENCE_TYPE_L = 3   # Lehrgang (Training)

def setup_test_database():
    """Create a temporary test database with sample data"""
    db_path = '/tmp/test_lehrgang_statistics.db'
    
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
            TeamId INTEGER,
            IsTdQualified INTEGER DEFAULT 0,
            IsBrandmeldetechniker INTEGER DEFAULT 0,
            IsBrandschutzbeauftragter INTEGER DEFAULT 0
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
            Type TEXT NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Notes TEXT,
            CreatedAt TEXT,
            CreatedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE TeamShiftAssignments (
            TeamId INTEGER NOT NULL,
            ShiftTypeId INTEGER NOT NULL,
            PRIMARY KEY (TeamId, ShiftTypeId),
            FOREIGN KEY (TeamId) REFERENCES Teams(Id),
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id)
        )
    """)
    
    # Insert test data
    cursor.execute("INSERT INTO Teams (Id, Name) VALUES (1, 'Team A')")
    
    # Create 3 test employees
    for emp_id in range(1, 4):
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, TeamId)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (emp_id, f'Employee{emp_id}', 'Test', f'EMP00{emp_id}', f'emp{emp_id}@test.de'))
    
    cursor.execute("""
        INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours)
        VALUES 
            (1, 'F', 'Frühdienst', '05:45', '13:45', 8.0),
            (2, 'S', 'Spätdienst', '13:45', '21:45', 8.0),
            (3, 'N', 'Nachtdienst', '21:45', '05:45', 8.0)
    """)
    
    # Assign shift types to team
    cursor.execute("""
        INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId)
        VALUES (1, 1), (1, 2), (1, 3)
    """)
    
    # Create 20 shifts for each employee (160 hours total each)
    # Planning for January 1-20, 2026
    for emp_id in range(1, 4):
        for day in range(1, 21):
            shift_date = date(2026, 1, day)
            shift_type_id = 1  # Early shift (F)
            
            cursor.execute("""
                INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
                VALUES (?, ?, ?, ?)
            """, (emp_id, shift_type_id, shift_date.isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    return conn, db_path


def get_statistics_for_employee(conn, employee_id, start_date, end_date):
    """Get statistics as calculated by the web API"""
    cursor = conn.cursor()
    
    # Get shift hours
    cursor.execute("""
        SELECT COUNT(sa.Id) as ShiftCount,
               COALESCE(SUM(st.DurationHours), 0) as ShiftHours
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.EmployeeId = ?
          AND sa.Date >= ? AND sa.Date <= ?
    """, (employee_id, start_date.isoformat(), end_date.isoformat()))
    
    shift_row = cursor.fetchone()
    shift_count = shift_row['ShiftCount'] if shift_row else 0
    shift_hours = float(shift_row['ShiftHours'] or 0) if shift_row else 0.0
    
    # Get Lehrgang hours separately
    # Note: Type is stored as INTEGER in database: 1=AU, 2=U, 3=L
    cursor.execute("""
        SELECT SUM(
                   CASE
                       WHEN a.StartDate >= ? AND a.EndDate <= ? THEN
                           julianday(a.EndDate) - julianday(a.StartDate) + 1
                       WHEN a.StartDate < ? AND a.EndDate <= ? THEN
                           julianday(a.EndDate) - julianday(?) + 1
                       WHEN a.StartDate >= ? AND a.EndDate > ? THEN
                           julianday(?) - julianday(a.StartDate) + 1
                       WHEN a.StartDate < ? AND a.EndDate > ? THEN
                           julianday(?) - julianday(?) + 1
                       ELSE 0
                   END
               ) * 8.0 as LehrgangHours
        FROM Absences a
        WHERE a.EmployeeId = ?
          AND a.Type = 3
          AND ((a.StartDate <= ? AND a.EndDate >= ?)
            OR (a.StartDate >= ? AND a.StartDate <= ?))
    """, (
        start_date.isoformat(), end_date.isoformat(),
        start_date.isoformat(), end_date.isoformat(), start_date.isoformat(),
        start_date.isoformat(), end_date.isoformat(), end_date.isoformat(),
        start_date.isoformat(), end_date.isoformat(), end_date.isoformat(), start_date.isoformat(),
        employee_id,
        end_date.isoformat(), start_date.isoformat(),
        start_date.isoformat(), end_date.isoformat()
    ))
    
    lehrgang_row = cursor.fetchone()
    lehrgang_hours = float(lehrgang_row['LehrgangHours'] or 0) if lehrgang_row else 0.0
    
    total_hours = shift_hours + lehrgang_hours
    
    return {
        'shiftCount': shift_count,
        'shiftHours': shift_hours,
        'lehrgangHours': lehrgang_hours,
        'totalHours': total_hours
    }


def test_all_absence_types():
    """
    Test that all three absence types are handled correctly:
    - Employee 1: AU (sick) for 5 days → Remove shifts, NO hours counted
    - Employee 2: U (vacation) for 5 days → Remove shifts, NO hours counted
    - Employee 3: L (training) for 5 days → Remove shifts, BUT count 8h/day
    """
    print("=" * 80)
    print("TEST: All Absence Types - AU, U, and L")
    print("=" * 80)
    
    # Setup test database
    conn, db_path = setup_test_database()
    
    try:
        from springer_replacement import process_absence_with_springer_assignment
        
        month_start = date(2026, 1, 1)
        month_end = date(2026, 1, 31)
        
        # Test Employee 1: AU (sick leave)
        print("\n" + "=" * 80)
        print("TEST CASE 1: AU (Sick Leave) - Employee 1")
        print("=" * 80)
        
        emp1_stats_before = get_statistics_for_employee(conn, 1, month_start, month_end)
        print(f"Before absence: {emp1_stats_before['shiftCount']} shifts, {emp1_stats_before['totalHours']}h")
        
        # Create AU absence for Jan 6-10 (5 days)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (1, ABSENCE_TYPE_AU, '2026-01-06', '2026-01-10', 
              'AU Test', datetime.now().isoformat()))
        
        absence_id = cursor.lastrowid
        conn.commit()
        
        results = process_absence_with_springer_assignment(
            conn, absence_id, 1, date(2026, 1, 6), date(2026, 1, 10), 1, 'test@test.de'
        )
        
        print(f"Shifts removed: {results['shiftsRemoved']}")
        
        emp1_stats_after = get_statistics_for_employee(conn, 1, month_start, month_end)
        print(f"After absence: {emp1_stats_after['shiftCount']} shifts, {emp1_stats_after['totalHours']}h")
        print(f"Expected: 15 shifts, 120h")
        
        # Verify: 20 - 5 = 15 shifts, 160h - 40h = 120h
        assert emp1_stats_after['shiftCount'] == 15, f"AU: Expected 15 shifts, got {emp1_stats_after['shiftCount']}"
        assert emp1_stats_after['totalHours'] == 120.0, f"AU: Expected 120h, got {emp1_stats_after['totalHours']}"
        print("✅ AU (sick leave): Shifts removed, hours NOT counted - CORRECT")
        
        # Test Employee 2: U (vacation)
        print("\n" + "=" * 80)
        print("TEST CASE 2: U (Urlaub/Vacation) - Employee 2")
        print("=" * 80)
        
        emp2_stats_before = get_statistics_for_employee(conn, 2, month_start, month_end)
        print(f"Before absence: {emp2_stats_before['shiftCount']} shifts, {emp2_stats_before['totalHours']}h")
        
        # Create U absence for Jan 6-10 (5 days)
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (2, ABSENCE_TYPE_U, '2026-01-06', '2026-01-10',
              'Urlaub Test', datetime.now().isoformat()))
        
        absence_id = cursor.lastrowid
        conn.commit()
        
        results = process_absence_with_springer_assignment(
            conn, absence_id, 2, date(2026, 1, 6), date(2026, 1, 10), 2, 'test@test.de'
        )
        
        print(f"Shifts removed: {results['shiftsRemoved']}")
        
        emp2_stats_after = get_statistics_for_employee(conn, 2, month_start, month_end)
        print(f"After absence: {emp2_stats_after['shiftCount']} shifts, {emp2_stats_after['totalHours']}h")
        print(f"Expected: 15 shifts, 120h")
        
        # Verify: 20 - 5 = 15 shifts, 160h - 40h = 120h
        assert emp2_stats_after['shiftCount'] == 15, f"U: Expected 15 shifts, got {emp2_stats_after['shiftCount']}"
        assert emp2_stats_after['totalHours'] == 120.0, f"U: Expected 120h, got {emp2_stats_after['totalHours']}"
        print("✅ U (vacation): Shifts removed, hours NOT counted - CORRECT")
        
        # Test Employee 3: L (Lehrgang/training)
        print("\n" + "=" * 80)
        print("TEST CASE 3: L (Lehrgang/Training) - Employee 3")
        print("=" * 80)
        
        emp3_stats_before = get_statistics_for_employee(conn, 3, month_start, month_end)
        print(f"Before absence: {emp3_stats_before['shiftCount']} shifts, {emp3_stats_before['totalHours']}h")
        
        # Create L absence for Jan 6-10 (5 days)
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (3, ABSENCE_TYPE_L, '2026-01-06', '2026-01-10',
              'Lehrgang Test', datetime.now().isoformat()))
        
        absence_id = cursor.lastrowid
        conn.commit()
        
        results = process_absence_with_springer_assignment(
            conn, absence_id, 3, date(2026, 1, 6), date(2026, 1, 10), 3, 'test@test.de'
        )
        
        print(f"Shifts removed: {results['shiftsRemoved']}")
        
        emp3_stats_after = get_statistics_for_employee(conn, 3, month_start, month_end)
        print(f"After absence: {emp3_stats_after['shiftCount']} shifts, {emp3_stats_after['totalHours']}h")
        print(f"  - Shift hours: {emp3_stats_after['shiftHours']}h")
        print(f"  - Lehrgang hours: {emp3_stats_after['lehrgangHours']}h")
        print(f"Expected: 15 shifts, 160h total (120h shifts + 40h training)")
        
        # Verify: 20 - 5 = 15 shifts, but hours = 120h (shifts) + 40h (5 days * 8h training) = 160h
        assert emp3_stats_after['shiftCount'] == 15, f"L: Expected 15 shifts, got {emp3_stats_after['shiftCount']}"
        assert emp3_stats_after['shiftHours'] == 120.0, f"L: Expected 120h shift hours, got {emp3_stats_after['shiftHours']}"
        assert emp3_stats_after['lehrgangHours'] == 40.0, f"L: Expected 40h training hours, got {emp3_stats_after['lehrgangHours']}"
        assert emp3_stats_after['totalHours'] == 160.0, f"L: Expected 160h total, got {emp3_stats_after['totalHours']}"
        print("✅ L (training): Shifts removed, but 8h/day STILL counted - CORRECT")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("Summary:")
        print("  ✓ AU (sick): Shifts removed, hours NOT counted")
        print("  ✓ U (vacation): Shifts removed, hours NOT counted")
        print("  ✓ L (training): Shifts removed, hours STILL counted (8h/day)")
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
    success = test_all_absence_types()
    exit(0 if success else 1)
