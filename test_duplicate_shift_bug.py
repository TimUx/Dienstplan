#!/usr/bin/env python3
"""
Test to reproduce the exact duplicate shift bug described in the problem statement.

When planning January 2026 (which extends to Feb 1) and then February 2026,
Feb 1 should have single shifts, not duplicates.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES, ShiftAssignment
import sqlite3
import os
import tempfile


def setup_database():
    """Create a test database with proper schema"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create schema
    cursor.execute("""
        CREATE TABLE Employees (
            Id TEXT PRIMARY KEY,
            PersonnelNumber TEXT,
            Name TEXT,
            TeamId TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Teams (
            Id TEXT PRIMARY KEY,
            Name TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftTypes (
            Id TEXT PRIMARY KEY,
            Code TEXT,
            Name TEXT,
            StartTime TEXT,
            EndTime TEXT,
            WorkingHours REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ShiftAssignments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId TEXT,
            ShiftTypeId TEXT,
            Date TEXT,
            IsManual INTEGER DEFAULT 0,
            IsFixed INTEGER DEFAULT 0,
            CreatedAt TEXT,
            CreatedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id)
        )
    """)
    
    conn.commit()
    return conn, db_path


def save_assignments(conn, assignments, created_by="Test", locked_employee_shift=None):
    """Save assignments to database, mimicking web_api.py logic"""
    if locked_employee_shift is None:
        locked_employee_shift = {}
    
    cursor = conn.cursor()
    
    # Debug: print first few locked assignments
    if locked_employee_shift:
        print(f"    Debug: First 3 locked assignments:")
        for i, ((emp_id, d), shift) in enumerate(list(locked_employee_shift.items())[:3]):
            print(f"      ({emp_id}, {d}) -> {shift}")
    
    # Debug: print first few assignments to insert
    if assignments:
        print(f"    Debug: First 3 assignments to insert:")
        for i, a in enumerate(assignments[:3]):
            print(f"      ({a.employee_id}, {a.date})")
    
    skipped = 0
    inserted = 0
    for assignment in assignments:
        # Skip if this assignment is locked (already exists from previous planning)
        if (assignment.employee_id, assignment.date) in locked_employee_shift:
            skipped += 1
            continue
        
        cursor.execute("""
            INSERT INTO ShiftAssignments 
            (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            assignment.employee_id,
            assignment.shift_type_id,
            assignment.date.isoformat(),
            0,
            0,
            created_by
        ))
        inserted += 1
    
    conn.commit()
    print(f"  → Inserted {inserted} assignments, skipped {skipped} locked assignments")


def delete_assignments_for_range(conn, start_date, end_date):
    """Delete non-fixed assignments in range, mimicking web_api.py logic"""
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM ShiftAssignments 
        WHERE Date >= ? AND Date <= ? AND IsFixed = 0
    """, (start_date.isoformat(), end_date.isoformat()))
    conn.commit()


def load_existing_assignments(conn, start_date, end_date):
    """Load existing assignments as locked constraints"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sa.EmployeeId, sa.Date, st.Code
        FROM ShiftAssignments sa
        INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.Date >= ? AND sa.Date <= ?
    """, (start_date.isoformat(), end_date.isoformat()))
    
    locked_employee_shift = {}
    for emp_id, date_str, shift_code in cursor.fetchall():
        assignment_date = date.fromisoformat(date_str)
        # Convert to int to match assignment.employee_id type
        try:
            emp_id_int = int(emp_id)
        except (ValueError, TypeError):
            emp_id_int = emp_id
        locked_employee_shift[(emp_id_int, assignment_date)] = shift_code
    
    return locked_employee_shift


def count_assignments_on_date(conn, target_date):
    """Count how many times each employee has an assignment on a specific date"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.Name, st.Code, COUNT(*) as cnt
        FROM ShiftAssignments sa
        INNER JOIN Employees e ON sa.EmployeeId = e.Id
        INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.Date = ?
        GROUP BY e.Id, st.Code
        HAVING COUNT(*) > 1
    """, (target_date.isoformat(),))
    
    return cursor.fetchall()


def main():
    print("=" * 80)
    print("TEST: Reproduce Duplicate Shift Bug (January → February 2026)")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    conn, db_path = setup_database()
    
    try:
        # Initialize database
        cursor = conn.cursor()
        for team in teams:
            cursor.execute("INSERT INTO Teams (Id, Name) VALUES (?, ?)", 
                         (team.id, team.name))
        for emp in employees:
            cursor.execute("INSERT INTO Employees (Id, PersonnelNumber, Name, TeamId) VALUES (?, ?, ?, ?)",
                         (emp.id, emp.personalnummer, emp.name, emp.team_id))
        for st in STANDARD_SHIFT_TYPES:
            cursor.execute("""
                INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, WorkingHours) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (st.id, st.code, st.name, st.start_time, st.end_time, st.hours))
        conn.commit()
        
        # ====================================================================
        # STEP 1: Plan January 2026 (extends to Feb 1)
        # ====================================================================
        print("\n" + "=" * 80)
        print("STEP 1: Planning January 2026")
        print("=" * 80)
        
        jan_start = date(2026, 1, 1)  # Thursday
        jan_end = date(2026, 1, 31)   # Saturday
        
        # Extend to complete week (next Sunday is Feb 1)
        jan_extended_start = jan_start - timedelta(days=jan_start.weekday() + 1)  # Previous Sunday (Dec 28)
        jan_extended_end = jan_end + timedelta(days=(6 - jan_end.weekday()))  # Next Sunday (Feb 1)
        
        print(f"Requested: {jan_start} to {jan_end}")
        print(f"Extended:  {jan_extended_start} to {jan_extended_end}")
        print(f"  → Includes Feb 1: {jan_extended_end}")
        
        # Plan January
        jan_model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=jan_extended_start,
            end_date=jan_extended_end,
            absences=[],
            shift_types=STANDARD_SHIFT_TYPES
        )
        jan_model.global_settings = global_settings
        
        jan_result = solve_shift_planning(jan_model, time_limit_seconds=60, 
                                          global_settings=global_settings)
        
        if not jan_result:
            print("❌ Failed to plan January!")
            return False
        
        jan_assignments, _, _ = jan_result
        
        # Filter to save only Jan 1 - Feb 1 (mimicking web_api filtering)
        jan_save_assignments = [a for a in jan_assignments if jan_start <= a.date <= jan_extended_end]
        
        print(f"✓ Generated {len(jan_assignments)} total assignments")
        print(f"  Saving: {len(jan_save_assignments)} assignments (Jan 1 - Feb 1)")
        
        # Count Feb 1 assignments
        feb_1 = date(2026, 2, 1)
        feb_1_from_jan = [a for a in jan_save_assignments if a.date == feb_1]
        print(f"  → {len(feb_1_from_jan)} assignments on Feb 1 from January planning")
        
        # Save to database (no need to delete first, DB is empty)
        save_assignments(conn, jan_save_assignments, "January Planning")
        print("✓ Saved to database")
        
        # Check database
        cursor.execute("SELECT COUNT(*) FROM ShiftAssignments WHERE Date = ?", (feb_1.isoformat(),))
        count_in_db = cursor.fetchone()[0]
        print(f"✓ Database check: {count_in_db} assignments on Feb 1")
        
        # ====================================================================
        # STEP 2: Plan February 2026 (starts from Feb 1)
        # ====================================================================
        print("\n" + "=" * 80)
        print("STEP 2: Planning February 2026")
        print("=" * 80)
        
        feb_start = date(2026, 2, 1)  # Sunday
        feb_end = date(2026, 2, 28)   # Saturday
        
        # Extend to complete week
        feb_extended_start = feb_start  # Already Sunday
        feb_extended_end = feb_end + timedelta(days=1)  # March 1 (Sunday)
        
        print(f"Requested: {feb_start} to {feb_end}")
        print(f"Extended:  {feb_extended_start} to {feb_extended_end}")
        
        # Load existing assignments (this is what web_api does)
        locked_employee_shift = load_existing_assignments(conn, feb_extended_start, feb_extended_end)
        print(f"\n✓ Loaded {len(locked_employee_shift)} locked employee assignments")
        
        feb_1_locked = sum(1 for (emp_id, d) in locked_employee_shift.keys() if d == feb_1)
        print(f"  → {feb_1_locked} locked assignments on Feb 1")
        
        # Plan February with locked constraints
        feb_model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=feb_extended_start,
            end_date=feb_extended_end,
            absences=[],
            shift_types=STANDARD_SHIFT_TYPES,
            locked_employee_shift=locked_employee_shift
        )
        feb_model.global_settings = global_settings
        
        feb_result = solve_shift_planning(feb_model, time_limit_seconds=60, 
                                          global_settings=global_settings)
        
        if not feb_result:
            print("❌ Failed to plan February!")
            return False
        
        feb_assignments, _, _ = feb_result
        
        # Filter to save only Feb 1 - Mar 1 (mimicking web_api filtering)
        feb_save_assignments = [a for a in feb_assignments if feb_start <= a.date <= feb_extended_end]
        
        print(f"\n✓ Generated {len(feb_assignments)} total assignments")
        print(f"  Saving: {len(feb_save_assignments)} assignments (Feb 1 - Mar 1)")
        
        feb_1_from_feb = [a for a in feb_save_assignments if a.date == feb_1]
        print(f"  → {len(feb_1_from_feb)} assignments on Feb 1 from February planning")
        if feb_1_from_feb:
            print(f"    Employee IDs for Feb 1 from planning: {sorted(set(a.employee_id for a in feb_1_from_feb))}")
        if locked_employee_shift:
            feb_1_locked_ids = sorted(set(emp_id for (emp_id, d) in locked_employee_shift.keys() if d == feb_1))
            print(f"    Employee IDs locked for Feb 1: {feb_1_locked_ids}")
        
        # THIS IS THE KEY: web_api only deletes if force=True
        # Simulating force=False (the default behavior)
        force = False
        if force:
            delete_assignments_for_range(conn, feb_start, feb_extended_end)
            print(f"\n✓ Deleted existing non-fixed assignments from {feb_start} to {feb_extended_end}")
        else:
            print(f"\n⚠️  NOT deleting (force=False) - this should trigger the bug!")
        
        # Check database after delete
        cursor.execute("SELECT COUNT(*) FROM ShiftAssignments WHERE Date = ?", (feb_1.isoformat(),))
        count_after_delete = cursor.fetchone()[0]
        print(f"  → Database has {count_after_delete} assignments on Feb 1 after delete")
        
        save_assignments(conn, feb_save_assignments, "February Planning", locked_employee_shift=locked_employee_shift)
        print("✓ Saved to database")
        
        # ====================================================================
        # STEP 3: Check for duplicates
        # ====================================================================
        print("\n" + "=" * 80)
        print("STEP 3: Checking for Duplicate Shifts")
        print("=" * 80)
        
        # Check total count on Feb 1
        cursor.execute("SELECT COUNT(*) FROM ShiftAssignments WHERE Date = ?", (feb_1.isoformat(),))
        total_on_feb_1 = cursor.fetchone()[0]
        print(f"\nTotal assignments on Feb 1: {total_on_feb_1}")
        print(f"Expected: {len(feb_1_from_feb)}")
        
        # Check for duplicates
        duplicates = count_assignments_on_date(conn, feb_1)
        
        if duplicates:
            print(f"\n❌ FOUND DUPLICATES ON FEB 1:")
            for emp_name, shift_code, count in duplicates:
                print(f"  - {emp_name}: {shift_code} (x{count})")
            print("\n" + "=" * 80)
            print("❌ TEST FAILED - Bug reproduced!")
            print("=" * 80)
            return False
        else:
            print("\n✓ No duplicates found")
            print("\n" + "=" * 80)
            print("✓ TEST PASSED - No duplicate shifts!")
            print("=" * 80)
            return True
        
    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
