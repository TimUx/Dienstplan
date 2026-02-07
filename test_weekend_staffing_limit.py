"""
Test for weekend staffing limit (max 12 total employees across all shifts).

This test verifies that the solver respects the requirement:
"Ein Maximum von 12 Mitarbeitern an Wochenenden sollte nicht überschritten werden."
(A maximum of 12 employees on weekends should not be exceeded.)

The constraint is implemented as a soft constraint with high priority (150),
which is higher than hours shortage (100) to ensure it's respected.
"""

import sqlite3
from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
from data_loader import load_employees_from_db, load_teams_from_db, load_shift_types_from_db


def count_weekend_employees(solution, saturday, sunday):
    """Count unique employees working on each weekend day."""
    sat_employees = set()
    sun_employees = set()
    
    for assignment in solution:
        if assignment.date == saturday:
            sat_employees.add(assignment.employee_id)
        elif assignment.date == sunday:
            sun_employees.add(assignment.employee_id)
    
    return len(sat_employees), len(sun_employees)


def test_weekend_limit():
    """Test that weekend staffing is limited to max 12 employees."""
    print("=" * 70)
    print("TEST: Weekend Staffing Limit (Max 12 Employees)")
    print("=" * 70)
    
    # Initialize test database
    db_path = "dienstplan.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load data
    print("\n[1/5] Loading data from database...")
    employees = load_employees_from_db(db_path)
    teams = load_teams_from_db(db_path)
    shift_types = load_shift_types_from_db(db_path)
    
    print(f"  - Employees: {len(employees)}")
    print(f"  - Teams: {len(teams)}")
    print(f"  - Shift types: {len(shift_types)}")
    
    # Plan for one week that includes a weekend
    start_date = date(2026, 3, 2)  # Monday
    end_date = date(2026, 3, 8)    # Sunday
    
    print(f"\n[2/5] Planning period: {start_date} to {end_date}")
    print(f"  - Saturday: {date(2026, 3, 7)}")
    print(f"  - Sunday: {date(2026, 3, 8)}")
    
    # Create model
    print("\n[3/5] Creating planning model...")
    planning_model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=[],
        shift_types=shift_types
    )
    
    # Create solver with shorter time limit for testing
    print("\n[4/5] Running solver...")
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=30,
        num_workers=4,
        db_path=db_path
    )
    
    # Solve
    solution, status_msg, stats = solver.solve()
    
    print(f"  - Status: {status_msg}")
    print(f"  - Assignments: {len(solution)}")
    
    # Check weekend staffing
    print("\n[5/5] Checking weekend staffing...")
    saturday = date(2026, 3, 7)
    sunday = date(2026, 3, 8)
    
    sat_count, sun_count = count_weekend_employees(solution, saturday, sunday)
    
    print(f"  - Saturday employees: {sat_count}")
    print(f"  - Sunday employees: {sun_count}")
    
    # Verify constraint
    max_allowed = 12
    sat_ok = sat_count <= max_allowed
    sun_ok = sun_count <= max_allowed
    
    print("\n" + "=" * 70)
    if sat_ok and sun_ok:
        print("✓ TEST PASSED: Weekend staffing is within limit")
        print(f"  Saturday: {sat_count}/{max_allowed} ✓")
        print(f"  Sunday: {sun_count}/{max_allowed} ✓")
    else:
        print("✗ TEST FAILED: Weekend staffing exceeds limit")
        if not sat_ok:
            print(f"  Saturday: {sat_count}/{max_allowed} ✗ (exceeded by {sat_count - max_allowed})")
        if not sun_ok:
            print(f"  Sunday: {sun_count}/{max_allowed} ✗ (exceeded by {sun_count - max_allowed})")
    print("=" * 70)
    
    conn.close()
    
    # Return test result
    return sat_ok and sun_ok


if __name__ == "__main__":
    try:
        success = test_weekend_limit()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
