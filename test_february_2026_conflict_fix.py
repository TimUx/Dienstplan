#!/usr/bin/env python3
"""
Test for the February 2026 locked team shift conflict fix.

This test specifically targets the bug where multiple employees from the SAME team
have different locked shifts for the same week, which caused INFEASIBLE errors.

The bug occurred when:
1. Employee A from Team 1 has locked shift "F" for week 0
2. Employee B from Team 1 has locked shift "N" for week 0
3. Both constraints were added: team_shift[(1, 0, "F")] == 1 AND team_shift[(1, 0, "N")] == 1
4. But sum of all shifts for team/week must equal 1 → INFEASIBLE
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def test_conflicting_locked_shifts_same_team():
    """
    Test that conflicting locked shifts for the same team/week are handled gracefully.
    
    This is the specific bug that caused February 2026 planning to fail.
    """
    
    print("=" * 80)
    print("TEST: Conflicting Locked Shifts - Same Team, Same Week")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Find a team with at least 2 employees
    team_with_multiple_employees = None
    for team in teams:
        team_employees = [emp for emp in employees if emp.team_id == team.id]
        if len(team_employees) >= 2:
            team_with_multiple_employees = team
            break
    
    if not team_with_multiple_employees:
        print("ERROR: Could not find a team with at least 2 employees")
        return False
    
    team_employees = [emp for emp in employees if emp.team_id == team_with_multiple_employees.id]
    emp1 = team_employees[0]
    emp2 = team_employees[1]
    
    print(f"\nTeam: {team_with_multiple_employees.name} (ID: {team_with_multiple_employees.id})")
    print(f"Employee 1: {emp1.name} (ID: {emp1.id})")
    print(f"Employee 2: {emp2.name} (ID: {emp2.id})")
    
    # Create CONFLICTING locked shifts for the same team/week
    # Both employees work on dates in the first week of February
    feb_start = date(2026, 2, 1)   # Sunday (start of planning period)
    feb_end = date(2026, 2, 28)
    
    # Sunday Feb 1 and Monday Feb 2 are in the same week (week 0)
    sunday_feb_1 = date(2026, 2, 1)
    monday_feb_2 = date(2026, 2, 2)
    
    locked_employee_shift = {
        (emp1.id, sunday_feb_1): "F",    # Employee 1 works F on Sunday
        (emp2.id, monday_feb_2): "N",    # Employee 2 works N on Monday (SAME WEEK, DIFFERENT SHIFT!)
    }
    
    print(f"\nCreating CONFLICTING locked shifts (same team, same week, different shifts):")
    print(f"  - {emp1.name} on {sunday_feb_1}: F")
    print(f"  - {emp2.name} on {monday_feb_2}: N")
    print(f"  → Both dates are in week 0, but team can only have ONE shift per week!")
    
    print(f"\nBEFORE FIX: This would cause INFEASIBLE (team forced to F AND N)")
    print(f"AFTER FIX: System should detect conflict and skip one lock gracefully")
    
    # Create model with conflicting locked constraints
    print(f"\nCreating February 2026 model with conflicting locks...")
    
    try:
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
        
        # Check that locked_team_shift has only ONE entry for this team/week
        team_week_locks = [(t, w, s) for (t, w), s in feb_model.locked_team_shift.items() 
                          if t == team_with_multiple_employees.id and w == 0]
        
        print(f"\nModel locked_team_shift for Team {team_with_multiple_employees.id}, Week 0:")
        if team_week_locks:
            for t, w, s in team_week_locks:
                print(f"  - Team {t}, Week {w} -> {s}")
        else:
            print(f"  (none - no conflicting locks)")
        
        if len(team_week_locks) > 1:
            print(f"\n❌ ERROR: Multiple locks for same team/week - should have been prevented!")
            return False
        
        # Try to solve
        print(f"\nSolving February 2026 (time limit: 30s)...")
        feb_result = solve_shift_planning(feb_model, time_limit_seconds=30, 
                                         global_settings=global_settings)
        
        if not feb_result:
            print("\n❌ FAILED to plan February!")
            print("  The fix did not prevent INFEASIBLE")
            return False
        
        print(f"✓ February planned successfully!")
        print(f"  System handled conflicting locks gracefully")
        
    except Exception as e:
        print(f"\n❌ EXCEPTION during model creation or solving:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✓ TEST PASSED - Conflicting locks handled gracefully!")
    print("=" * 80)
    return True


def test_february_2026_full_scenario():
    """
    Test the full February 2026 scenario as described in the problem statement.
    
    This simulates planning January, then planning February with locked shifts from January.
    """
    
    print("\n" * 2)
    print("=" * 80)
    print("TEST: Full January → February 2026 Scenario")
    print("=" * 80)
    
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Step 1: Plan January 2026
    print("\n1. Planning January 2026...")
    jan_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES
    )
    jan_model.global_settings = global_settings
    
    jan_result = solve_shift_planning(jan_model, time_limit_seconds=30, 
                                      global_settings=global_settings)
    
    if not jan_result:
        print("   ❌ January planning FAILED (unexpected)")
        return False
    
    jan_assignments, _, _ = jan_result
    print(f"   ✓ January planned: {len(jan_assignments)} assignments")
    
    # Extract locked employee shifts from January that fall into February's planning window
    # February planning starts on Feb 1, but includes week starting Jan 27 (Mon) to Feb 2 (Sun)
    feb_planning_start = date(2026, 2, 1)
    
    # In reality, weeks are Mon-Sun, so February planning would include:
    # Week starting Jan 27 (Mon Jan 27 - Sun Feb 2)
    # This means any January assignments from Jan 27-31 would be locked in February planning
    
    locked_employee_shift = {}
    for assignment in jan_assignments:
        if assignment.date >= date(2026, 1, 27) and assignment.date < feb_planning_start:
            # This assignment would be loaded as a locked constraint when planning February
            shift_code = next((st.code for st in STANDARD_SHIFT_TYPES 
                             if st.id == assignment.shift_type_id), None)
            if shift_code:
                locked_employee_shift[(assignment.employee_id, assignment.date)] = shift_code
    
    print(f"\n2. Simulating January assignments extending into February's first week:")
    print(f"   Found {len(locked_employee_shift)} locked assignments from Jan 27-31")
    
    # Step 2: Plan February 2026 with locked shifts from January
    print("\n3. Planning February 2026 with locked shifts...")
    feb_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES,
        locked_employee_shift=locked_employee_shift
    )
    feb_model.global_settings = global_settings
    
    print(f"   Model created with {len(feb_model.locked_team_shift)} locked team/week assignments")
    
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=30, 
                                      global_settings=global_settings)
    
    if not feb_result:
        print("\n   ❌ February planning FAILED!")
        print("   This is the bug we're fixing")
        return False
    
    feb_assignments, _, _ = feb_result
    print(f"   ✓ February planned: {len(feb_assignments)} assignments")
    
    print("\n" + "=" * 80)
    print("✓ TEST PASSED - Full scenario works!")
    print("  - January 2026: ✓")
    print("  - February 2026 with locked shifts: ✓")
    print("=" * 80)
    return True


if __name__ == "__main__":
    # Run both tests
    test1_passed = test_conflicting_locked_shifts_same_team()
    test2_passed = test_february_2026_full_scenario()
    
    success = test1_passed and test2_passed
    
    print("\n" * 2)
    print("=" * 80)
    print("OVERALL RESULTS:")
    print(f"  Conflict handling test: {'✓ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Full scenario test: {'✓ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 80)
    
    exit(0 if success else 1)
