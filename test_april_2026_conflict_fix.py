#!/usr/bin/env python3
"""
Test for April 2026 conflict fix - reproduces the exact user scenario.

This test verifies that when planning April 2026 with conflicting team assignments
from March in week 0, the system properly detects and removes conflicting locks
to allow the solver to find a solution.

User Issue:
- Planning April 2026 failed with INFEASIBLE
- Many warnings: "WARNING: Skipping conflicting locked shift for team X, week 0"
- All showed "Existing: F, Attempted: S or N"
- Dates involved: March 30-31, April 1-5 (week 0)
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def test_april_2026_conflicting_locks():
    """
    Test that April 2026 planning works when there are conflicting team locks
    from March assignments.
    
    Scenario:
    - April 1, 2026 is a Wednesday
    - Planning extends back to Monday, March 30 (week 0 = March 30 - April 5)
    - Database has existing team assignments with conflicting shift codes for week 0
    - System should detect conflicts and remove team locks for week 0
    - Planning should succeed
    """
    
    print("=" * 80)
    print("TEST: April 2026 Conflicting Team Locks Fix")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Find teams
    team1 = next((t for t in teams if t.id == 1), None)
    team3 = next((t for t in teams if t.id == 3), None)
    if not team1 or not team3:
        print("ERROR: Could not find required teams")
        return False
    
    # Get employees from teams
    team1_employees = [emp for emp in employees if emp.team_id == 1]
    team3_employees = [emp for emp in employees if emp.team_id == 3]
    
    print(f"\nTeam 1: {team1.name} with {len(team1_employees)} employees")
    print(f"Team 3: {team3.name} with {len(team3_employees)} employees")
    
    # April 2026 planning period
    april_start = date(2026, 4, 1)   # Wednesday
    april_end = date(2026, 4, 30)    # Thursday
    
    print(f"\nApril planning: {april_start} to {april_end}")
    print(f"Week 0 spans: March 30 (Mon) to April 5 (Sun)")
    
    # Simulate conflicting team locks from database
    # This represents what web_api.py would load from existing ShiftAssignments
    # In the user's case, different employees from the same team worked different
    # shifts on different days in March, creating conflicts when grouped by week
    locked_team_shift_with_conflicts = {
        # Team 1, week 0 is locked to 'F' (from some March 30 assignment)
        (1, 0): 'F',
        # Team 3, week 0 is also locked to 'F' (from some March 31 assignment)
        (3, 0): 'F',
    }
    
    # Simulate employee locks that conflict with team locks
    # These represent individual employee assignments that the system loaded
    # In the user's scenario, employees worked 'S' and 'N' shifts, but team was locked to 'F'
    locked_employee_shift_with_conflicts = {}
    
    if len(team1_employees) >= 3:
        # Team 1 employees worked different shifts on March 30-April 1
        locked_employee_shift_with_conflicts[(team1_employees[0].id, date(2026, 3, 30))] = "S"
        locked_employee_shift_with_conflicts[(team1_employees[1].id, date(2026, 3, 31))] = "S"
        locked_employee_shift_with_conflicts[(team1_employees[2].id, date(2026, 4, 1))] = "N"
    
    if len(team3_employees) >= 3:
        # Team 3 employees also worked different shifts
        locked_employee_shift_with_conflicts[(team3_employees[0].id, date(2026, 3, 30))] = "N"
        locked_employee_shift_with_conflicts[(team3_employees[1].id, date(2026, 3, 31))] = "N"
        locked_employee_shift_with_conflicts[(team3_employees[2].id, date(2026, 4, 1))] = "S"
    
    print(f"\nSimulating conflicting locks:")
    print(f"  - Team locks: {locked_team_shift_with_conflicts}")
    print(f"  - Employee locks: {len(locked_employee_shift_with_conflicts)} assignments")
    print(f"\nExpected behavior:")
    print(f"  - model.py should detect conflicts and print warnings")
    print(f"  - model.py should skip conflicting team locks")
    print(f"  - Solver should find a feasible solution")
    
    # Create model with conflicting locks
    print(f"\nCreating April 2026 model with conflicting locks...")
    
    try:
        model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=april_start,
            end_date=april_end,
            absences=[],
            shift_types=STANDARD_SHIFT_TYPES,
            locked_team_shift=locked_team_shift_with_conflicts,
            locked_employee_shift=locked_employee_shift_with_conflicts
        )
        model.global_settings = global_settings
        
        print(f"✓ Model created successfully")
        
        # The model should have processed and potentially modified the locks
        print(f"\nFinal locked_team_shift in model: {len(model.locked_team_shift)} entries")
        
        # Try to solve
        print(f"\nAttempting to solve April 2026 model...")
        result = solve_shift_planning(
            planning_model=model,
            time_limit_seconds=60,
            num_workers=4,
            global_settings=global_settings
        )
        
        if result is not None:
            print(f"✓ SUCCESS: April 2026 planning completed despite conflicting locks")
            print(f"  - Model handled conflicts gracefully")
            print(f"  - Solver found a feasible solution")
            return True
        else:
            print(f"✗ FAIL: Planning returned None (INFEASIBLE)")
            print(f"  - Fix did not work - conflicts still causing INFEASIBLE")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Exception during planning: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_april_2026_conflicting_locks()
    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED")
        exit(0)
    else:
        print("✗ TEST FAILED")
        exit(1)
