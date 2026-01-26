#!/usr/bin/env python3
"""
Integration test for February 2026 planning with locked constraints.

This test simulates the real-world scenario where:
1. January 2026 planning extends to complete weeks (potentially into early February)
2. February 2026 planning loads those existing assignments as locked constraints
3. The system should successfully plan February without INFEASIBLE errors
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def test_february_with_locked_constraints():
    """
    Test February 2026 planning with simulated locked constraints from January.
    
    This reproduces the real-world scenario where month boundaries create
    locked employee shifts that must not conflict with rotation constraints.
    """
    
    print("=" * 80)
    print("TEST: February 2026 with Locked Constraints")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # February 2026 date range
    feb_start = date(2026, 2, 1)   # Sunday
    feb_end = date(2026, 2, 28)     # Saturday
    
    # Simulate locked employee shifts from January planning that extend into February
    # In reality, these would come from the database (existing ShiftAssignments)
    locked_employee_shift = {}
    
    # Simulate that January planning extended to Sunday, Feb 1st
    # Let's lock the first few employees to specific shifts on Feb 1st
    sunday_feb_1 = date(2026, 2, 1)
    
    # Get employees from different teams to avoid conflicts
    # (all team members must work the same shift on the same day)
    teams_used = set()
    employees_with_teams = []
    for emp in employees:
        if emp.team_id and emp.team_id not in teams_used:
            employees_with_teams.append(emp)
            teams_used.add(emp.team_id)
            if len(employees_with_teams) >= 3:
                break
    
    print(f"\nSimulating locked assignments from January planning:")
    print(f"Date: {sunday_feb_1} (first Sunday of February)")
    
    # Lock employees from different teams to different shifts - simulating January's last week
    shift_codes = ["F", "N", "S"]
    for i, emp in enumerate(employees_with_teams):
        shift_code = shift_codes[i % 3]
        locked_employee_shift[(emp.id, sunday_feb_1)] = shift_code
        print(f"  - {emp.name} (Team {emp.team_id}): {shift_code}")
    
    print(f"\nTotal locked constraints: {len(locked_employee_shift)}")
    
    # Create model with locked constraints
    print(f"\nCreating February 2026 model with locked constraints...")
    feb_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=feb_start,
        end_date=feb_end,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES,
        locked_employee_shift=locked_employee_shift
    )
    feb_model.global_settings = global_settings
    
    # Verify that locked_team_shift was properly updated
    print(f"Model locked_team_shift entries: {len(feb_model.locked_team_shift)}")
    for (team_id, week_idx), shift in feb_model.locked_team_shift.items():
        print(f"  - Team {team_id}, Week {week_idx} -> {shift}")
    
    # Try to solve (with shorter time limit for faster testing)
    print(f"\nSolving February 2026 (time limit: 30s)...")
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=30, 
                                      global_settings=global_settings)
    
    if not feb_result:
        print("\n❌ FAILED to plan February with locked constraints!")
        print("  This indicates the fix did not work")
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        return False
    
    feb_assignments, _, _ = feb_result
    print(f"✓ February planned successfully: {len(feb_assignments)} assignments")
    
    # Verify locked constraints were respected
    print(f"\nVerifying locked constraints were respected...")
    violations = []
    for (emp_id, d), expected_shift in locked_employee_shift.items():
        # Find assignment for this employee on this date
        actual_assignments = [a for a in feb_assignments 
                            if a.employee_id == emp_id and a.date == d]
        
        if not actual_assignments:
            violations.append(f"Employee {emp_id} on {d}: expected {expected_shift}, got nothing")
        else:
            for assignment in actual_assignments:
                # Get shift code
                shift = next((st.code for st in STANDARD_SHIFT_TYPES 
                            if st.id == assignment.shift_type_id), "?")
                if shift != expected_shift:
                    violations.append(f"Employee {emp_id} on {d}: expected {expected_shift}, got {shift}")
    
    if violations:
        print(f"❌ Found {len(violations)} constraint violations:")
        for v in violations:
            print(f"  - {v}")
        print("\n" + "=" * 80)
        print("❌ TEST FAILED - Locked constraints not respected")
        print("=" * 80)
        return False
    
    print(f"✓ All {len(locked_employee_shift)} locked constraints respected")
    
    print("\n" + "=" * 80)
    print("✓ TEST PASSED - February 2026 planning works with locked constraints!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_february_with_locked_constraints()
    exit(0 if success else 1)
