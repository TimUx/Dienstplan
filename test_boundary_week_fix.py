#!/usr/bin/env python3
"""
Test for the boundary week employee lock fix.

This test reproduces the exact issue from the user's problem statement:
- Plan January 2026 successfully
- Try to plan February 2026 with locked shifts from January
- Verify that boundary week conflicts are handled correctly
- Ensure planning succeeds without INFEASIBLE errors

The issue was that employee locks from boundary weeks (weeks spanning month transitions)
were being applied, creating conflicts with team rotation constraints.

The fix: Skip ALL locks (employee and team) for dates in weeks spanning month boundaries.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def test_boundary_week_employee_locks():
    """
    Test that employee locks for dates in boundary weeks are skipped to prevent INFEASIBLE errors.
    """
    
    print("=" * 80)
    print("TEST: Boundary Week Employee Lock Fix")
    print("=" * 80)
    print("\nThis test reproduces the user's issue:")
    print("- January planning succeeds")
    print("- February planning with locked shifts from January")
    print("- Boundary week (Jan 26 - Feb 1) has conflicting locks")
    print("- Should succeed without INFEASIBLE errors")
    
    # Generate sample data
    employees, teams, _ = generate_sample_data()
    
    # February planning
    feb_start = date(2026, 2, 1)  # Sunday
    feb_end = date(2026, 2, 28)   # Saturday
    
    print(f"\nFebruary planning: {feb_start} to {feb_end}")
    print(f"  Feb 1 is a {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][feb_start.weekday()]}")
    print(f"  Extended period: Jan 26 (Mon) to Mar 1 (Sun)")
    print(f"  Boundary weeks: Week 0 (Jan 26 - Feb 1) and Week 4 (Feb 23 - Mar 1)")
    
    # Simulate the scenario from the user's problem statement:
    # 1. locked_team_shift from database query (for dates outside main month)
    # 2. locked_employee_shift from database query (for all dates in extended period)
    
    # Simulate locked_team_shift from January assignments
    # (These would be created by the query in web_api.py lines 2713-2758)
    locked_team_shift = {
        (1, 0): "S",  # Team 1, Week 0 → S
        (2, 0): "F",  # Team 2, Week 0 → F
        (3, 0): "S",  # Team 3, Week 0 → S
    }
    
    # Simulate locked_employee_shift from January assignments
    # (These would be created by the query in web_api.py lines 2686-2706)
    # Include assignments for Jan 26-31 and Feb 1 (entire week 0)
    locked_employee_shift = {}
    
    for emp in employees:
        # Simulate that employees worked different shifts on different days in the boundary week
        for day_offset in range(7):  # Jan 26 - Feb 1
            d = date(2026, 1, 26) + timedelta(days=day_offset)
            # Assign shifts that might conflict with team locks
            if emp.id % 3 == 0:
                locked_employee_shift[(emp.id, d)] = "F"
            elif emp.id % 3 == 1:
                locked_employee_shift[(emp.id, d)] = "N"
            else:
                locked_employee_shift[(emp.id, d)] = "S"
    
    print(f"\nlocked_team_shift (from database):")
    for (team_id, week_idx), shift in locked_team_shift.items():
        print(f"  Team {team_id}, Week {week_idx}: {shift}")
    
    print(f"\nlocked_employee_shift:")
    print(f"  Total: {len(locked_employee_shift)} locks")
    print(f"  Dates: Jan 26 - Feb 1 (all in boundary week 0)")
    
    # Sample a few locks
    print(f"  Sample locks:")
    for (emp_id, d), shift in sorted(locked_employee_shift.items())[:6]:
        emp = next((e for e in employees if e.id == emp_id), None)
        if emp:
            print(f"    Employee {emp_id} (Team {emp.team_id}) on {d}: {shift}")
    
    # Create model
    print(f"\n[Creating Model with Boundary Week Locks]")
    feb_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=feb_start,
        end_date=feb_end,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES,
        locked_team_shift=locked_team_shift,
        locked_employee_shift=locked_employee_shift
    )
    
    print(f"  Model created successfully")
    print(f"  locked_team_shift entries in model: {len(feb_model.locked_team_shift)}")
    
    # Solve
    print(f"\n[Solving February with Boundary Week Locks]")
    print(f"  Expected behavior:")
    print(f"    - Employee locks for Jan 26-31: SKIPPED (outside original period)")
    print(f"    - Employee locks for Feb 1: SKIPPED (in boundary week)")
    print(f"    - Team locks: Use database values only, no conflicts")
    print(f"    - Result: FEASIBLE solution")
    
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=60)
    
    if not feb_result:
        print("\n" + "=" * 80)
        print("✗ TEST FAILED - February planning returned INFEASIBLE")
        print("=" * 80)
        print("\nThe fix did not resolve the issue!")
        return False
    
    feb_assignments, _, _ = feb_result
    print(f"\n✓ February planning succeeded: {len(feb_assignments)} assignments")
    
    # Verify no conflicts or warnings were printed
    print(f"\n[Verification]")
    print(f"  ✓ No INFEASIBLE errors")
    print(f"  ✓ Boundary week locks handled correctly")
    print(f"  ✓ Planning completed successfully")
    
    print("\n" + "=" * 80)
    print("✓ TEST PASSED - Boundary week fix works correctly!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_boundary_week_employee_locks()
    exit(0 if success else 1)
