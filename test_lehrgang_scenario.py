#!/usr/bin/env python3
"""
Test to replicate the exact scenario from the issue:
- Employee "A" had 216h scheduled (27 shifts)
- A Lehrgang (training) for 7 days (Monday-Sunday) is added
- 6 shifts were removed from those 7 days (48h)
- Statistics should show: 216 - 48 + 56 = 224h
  (216h initial - 6 days * 8h shifts removed + 7 days * 8h training)
"""

import sqlite3
import os
from datetime import date, datetime, timezone
from entities import AbsenceType

def setup_scenario_database():
    """Create test database matching the issue scenario"""
    db_path = '/tmp/test_lehrgang_scenario.db'
    
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
    
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, TeamId)
        VALUES (13, 'Mitarbeiter', 'A', 'EMP013', 'a@test.de', 1)
    """)
    
    cursor.execute("""
        INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours)
        VALUES 
            (1, 'F', 'Frühdienst', '05:45', '13:45', 8.0),
            (2, 'S', 'Spätdienst', '13:45', '21:45', 8.0),
            (3, 'N', 'Nachtdienst', '21:45', '05:45', 8.0)
    """)
    
    cursor.execute("""
        INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId)
        VALUES (1, 1), (1, 2), (1, 3)
    """)
    
    # Create 27 shifts for employee A in January 2026 (216 hours)
    # This matches "216h" from the problem statement
    shift_dates = [
        # Week 1: Jan 1-5 (5 days, Thu-Mon)
        date(2026, 1, 1),  # Thu
        date(2026, 1, 2),  # Fri
        date(2026, 1, 3),  # Sat
        date(2026, 1, 4),  # Sun
        date(2026, 1, 5),  # Mon
        # Week 2: Jan 6-11 (6 days)
        date(2026, 1, 6),  # Tue
        date(2026, 1, 7),  # Wed
        date(2026, 1, 8),  # Thu
        date(2026, 1, 9),  # Fri
        date(2026, 1, 10), # Sat
        date(2026, 1, 11), # Sun
        # Week 3: Jan 13-19 (7 days, skip 12 which is Monday of Lehrgang week)
        date(2026, 1, 13), # Tue
        date(2026, 1, 14), # Wed
        date(2026, 1, 15), # Thu
        date(2026, 1, 16), # Fri
        date(2026, 1, 17), # Sat
        date(2026, 1, 18), # Sun
        date(2026, 1, 19), # Mon
        # Week 4: Jan 20-26 (7 days)
        date(2026, 1, 20), # Tue
        date(2026, 1, 21), # Wed
        date(2026, 1, 22), # Thu
        date(2026, 1, 23), # Fri
        date(2026, 1, 24), # Sat
        date(2026, 1, 25), # Sun
        date(2026, 1, 26), # Mon
        # Week 5: Jan 27-28 (2 days)
        date(2026, 1, 27), # Tue
        date(2026, 1, 28), # Wed
    ]
    
    for shift_date in shift_dates:
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, CreatedAt)
            VALUES (?, ?, ?, ?)
        """, (13, 1, shift_date.isoformat(), datetime.now().isoformat()))
    
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
          AND a.Type = 'L'
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


def test_exact_scenario():
    """
    Test the exact scenario from the issue:
    - Employee A has 216h (27 shifts of 8h each)
    - Lehrgang for 7 days (Jan 12-18, Monday to Sunday) is added
    - 6 shifts exist in those 7 days and are removed
    - Expected result: 216 - 48 + 56 = 224h
    """
    print("=" * 80)
    print("TEST: Exact Scenario from Issue")
    print("Employee A: 216h planned, Lehrgang for 7 days (6 shifts removed)")
    print("Expected: 216 - (6 * 8h) + (7 * 8h) = 224h")
    print("=" * 80)
    
    conn, db_path = setup_scenario_database()
    
    try:
        from springer_replacement import process_absence_with_springer_assignment
        
        month_start = date(2026, 1, 1)
        month_end = date(2026, 1, 31)
        
        # Check initial state
        print("\n" + "-" * 80)
        print("BEFORE LEHRGANG:")
        print("-" * 80)
        initial_stats = get_statistics_for_employee(conn, 13, month_start, month_end)
        print(f"Shifts: {initial_stats['shiftCount']}")
        print(f"Shift hours: {initial_stats['shiftHours']}h")
        print(f"Lehrgang hours: {initial_stats['lehrgangHours']}h")
        print(f"Total hours: {initial_stats['totalHours']}h")
        
        assert initial_stats['shiftCount'] == 27, f"Expected 27 initial shifts, got {initial_stats['shiftCount']}"
        assert initial_stats['totalHours'] == 216.0, f"Expected 216h initial, got {initial_stats['totalHours']}"
        print("✅ Initial state correct: 27 shifts, 216h")
        
        # Add Lehrgang for Jan 12-18 (7 days, Monday to Sunday)
        print("\n" + "-" * 80)
        print("ADDING LEHRGANG: Jan 12-18 (7 days, Monday to Sunday)")
        print("-" * 80)
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (13, AbsenceType.L.value, '2026-01-12', '2026-01-18', 
              'Lehrgang', datetime.now().isoformat()))
        
        absence_id = cursor.lastrowid
        conn.commit()
        
        # Process the absence (should remove shifts)
        results = process_absence_with_springer_assignment(
            conn, absence_id, 13, date(2026, 1, 12), date(2026, 1, 18), 13, 'test@test.de'
        )
        
        print(f"Shifts removed: {results['shiftsRemoved']}")
        
        # Check final state
        print("\n" + "-" * 80)
        print("AFTER LEHRGANG:")
        print("-" * 80)
        final_stats = get_statistics_for_employee(conn, 13, month_start, month_end)
        print(f"Shifts: {final_stats['shiftCount']}")
        print(f"Shift hours: {final_stats['shiftHours']}h")
        print(f"Lehrgang hours: {final_stats['lehrgangHours']}h")
        print(f"Total hours: {final_stats['totalHours']}h")
        
        # Calculate expected
        shifts_removed = results['shiftsRemoved']
        expected_shifts = 27 - shifts_removed
        expected_shift_hours = 216.0 - (shifts_removed * 8.0)
        expected_lehrgang_hours = 7 * 8.0  # 7 days * 8h
        expected_total_hours = expected_shift_hours + expected_lehrgang_hours
        
        print("\n" + "-" * 80)
        print("VERIFICATION:")
        print("-" * 80)
        print(f"Expected shifts: {expected_shifts} (27 - {shifts_removed})")
        print(f"Expected shift hours: {expected_shift_hours}h (216h - {shifts_removed * 8}h)")
        print(f"Expected Lehrgang hours: {expected_lehrgang_hours}h (7 days * 8h)")
        print(f"Expected total hours: {expected_total_hours}h")
        
        # Assertions
        assert final_stats['shiftCount'] == expected_shifts, \
            f"Expected {expected_shifts} shifts, got {final_stats['shiftCount']}"
        assert final_stats['shiftHours'] == expected_shift_hours, \
            f"Expected {expected_shift_hours}h shift hours, got {final_stats['shiftHours']}h"
        assert final_stats['lehrgangHours'] == expected_lehrgang_hours, \
            f"Expected {expected_lehrgang_hours}h Lehrgang hours, got {final_stats['lehrgangHours']}h"
        assert final_stats['totalHours'] == expected_total_hours, \
            f"Expected {expected_total_hours}h total, got {final_stats['totalHours']}h"
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED")
        print("=" * 80)
        print(f"Calculation: 216h - ({shifts_removed} shifts × 8h) + (7 days × 8h) = {expected_total_hours}h")
        print("The statistics correctly count Lehrgang days as 8h/day!")
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
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    success = test_exact_scenario()
    exit(0 if success else 1)
