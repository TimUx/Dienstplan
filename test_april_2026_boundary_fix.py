#!/usr/bin/env python3
"""
Test for April 2026 month boundary locked shift conflict fix.

This test verifies that when planning April 2026, locked shifts from March
that fall into week 0 (March 30 - April 5) don't cause conflicts because
team-level locks are skipped for weeks that span month boundaries.
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def test_april_2026_month_boundary():
    """
    Test that April 2026 planning works with locked shifts from March.
    
    Scenario:
    - April 1, 2026 is a Wednesday
    - Planning extends back to Monday, March 30
    - Week 0 is March 30 - April 5 (spans March/April boundary)
    - Locked employee shifts from March exist in week 0
    - Team-level locks should be skipped for week 0 to avoid conflicts
    """
    
    print("=" * 80)
    print("TEST: April 2026 Month Boundary - Locked Shift Conflicts")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Find Team Alpha (Team 1)
    team1 = next((t for t in teams if t.id == 1), None)
    if not team1:
        print("ERROR: Could not find Team Alpha (ID 1)")
        return False
    
    # Get employees from Team 1
    team1_employees = [emp for emp in employees if emp.team_id == 1]
    if len(team1_employees) < 3:
        print("ERROR: Team 1 needs at least 3 employees")
        return False
    
    print(f"\nTeam: {team1.name} (ID: {team1.id})")
    print(f"Team has {len(team1_employees)} employees")
    
    # April 2026 planning period
    april_start = date(2026, 4, 1)   # Wednesday
    april_end = date(2026, 4, 30)    # Thursday
    
    print(f"\nApril planning: {april_start} to {april_end}")
    print(f"April 1 is a {april_start.strftime('%A')}")
    
    # Extended dates (for display purposes)
    extended_start = date(2026, 3, 30)  # Monday (back from Wednesday)
    extended_end = date(2026, 5, 3)     # Sunday (forward from Thursday)
    print(f"Extended to: {extended_start} to {extended_end}")
    print(f"Week 0: {extended_start} to {date(2026, 4, 5)}")
    
    # Simulate locked shifts from March that fall into week 0
    # These represent employees who worked in March and their shifts
    # are now locked when planning April
    locked_employee_shift = {
        # Employee 2 worked Night shift on March 30 (Monday) - week 0
        (team1_employees[0].id, date(2026, 3, 30)): "N",
        # Employee 3 worked Night shift on March 31 (Tuesday) - week 0
        (team1_employees[1].id, date(2026, 3, 31)): "N",
        # Employee 4 worked Späte shift on April 1 (Wednesday) - week 0, but IN April
        (team1_employees[2].id, date(2026, 4, 1)): "S",
    }
    
    print(f"\nLocked employee shifts spanning March/April boundary:")
    for (emp_id, d), shift in sorted(locked_employee_shift.items()):
        emp = next((e for e in employees if e.id == emp_id), None)
        in_march = d < april_start
        print(f"  - Employee {emp_id} ({emp.name if emp else '?'}): {shift} on {d} ({'MARCH' if in_march else 'APRIL'})")
    
    print(f"\nExpected behavior:")
    print(f"  - Week 0 spans March/April boundary")
    print(f"  - Team-level locks should be SKIPPED for week 0")
    print(f"  - Only employee-level locks apply")
    print(f"  - Planning should succeed without conflicts")
    
    # Create model
    print(f"\nCreating April 2026 model...")
    
    try:
        model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=april_start,
            end_date=april_end,
            absences=[],
            shift_types=STANDARD_SHIFT_TYPES,
            locked_employee_shift=locked_employee_shift
        )
        model.global_settings = global_settings
        
        print(f"✓ Model created successfully")
        
        # Check that week 0 has NO team-level locks for Team 1
        team1_week0_locks = [(t, w, s) for (t, w), s in model.locked_team_shift.items() 
                             if t == team1.id and w == 0]
        
        print(f"\nTeam-level locks for Team {team1.id}, week 0: {len(team1_week0_locks)}")
        
        if len(team1_week0_locks) > 0:
            print(f"✗ FAIL: Week 0 should have NO team locks (spans month boundary)")
            for t, w, s in team1_week0_locks:
                print(f"    Team {t}, week {w}: {s}")
            return False
        else:
            print(f"✓ PASS: Week 0 has no team locks (correct behavior)")
        
        # Try to solve
        print(f"\nAttempting to solve April 2026 model...")
        result = solve_shift_planning(
            planning_model=model,
            time_limit_seconds=60,
            num_workers=4,
            global_settings=global_settings
        )
        
        if result is not None:
            print(f"✓ SUCCESS: April 2026 planning completed")
            return True
        else:
            print(f"✗ FAIL: Planning returned None (likely INFEASIBLE)")
            print(f"  This indicates the fix did not work properly")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Exception during planning: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_april_2026_month_boundary()
    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED")
        exit(0)
    else:
        print("✗ TEST FAILED")
        exit(1)
