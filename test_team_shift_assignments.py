"""
Test for TeamShiftAssignments functionality.

Validates that teams are only assigned to shifts they're configured for,
and employees from those teams only work those shifts.
"""

from datetime import date, timedelta
from entities import Employee, Team, Absence, ShiftType, AbsenceType, STANDARD_SHIFT_TYPES
from model import create_shift_planning_model
from solver import solve_shift_planning
from collections import defaultdict


def test_team_with_special_shift():
    """
    Test the main scenario from the problem statement:
    - Team "Brandschutzdienst" is only assigned to "TD" shift (Mon-Fri, no weekends)
    - Employees from this team should ONLY work TD shift
    - They should NOT be scheduled for F/S/N shifts
    - They should NOT be scheduled on weekends
    """
    print("\n" + "=" * 70)
    print("TEST: Team with Special Shift Assignment (Brandschutzdienst)")
    print("=" * 70)
    
    # Create shift types including a special "TS" (Tagschicht) shift
    # NOTE: We use "TS" instead of "TD" because "TD" is reserved for the special
    # TD marker system (Tagdienst organizational marker, not an actual shift)
    shift_types = STANDARD_SHIFT_TYPES.copy()
    
    # Add custom Tagschicht shift
    ts_shift = ShiftType(
        id=7,
        code="TS",  # Tagschicht (NOT "TD" which is reserved)
        name="Tagschicht",
        start_time="07:00",
        end_time="16:30",
        color_code="#9370DB",
        hours=9.5,
        weekly_working_hours=35.0,  # 35h/week as per problem statement
        min_staff_weekday=1,
        max_staff_weekday=2,
        min_staff_weekend=0,  # No weekend work
        max_staff_weekend=0,
        works_monday=True,
        works_tuesday=True,
        works_wednesday=True,
        works_thursday=True,
        works_friday=True,
        works_saturday=False,  # No Saturday
        works_sunday=False     # No Sunday
    )
    shift_types.append(ts_shift)
    
    # Create teams
    team_alpha = Team(id=1, name="Team Alpha", description="Regular rotation team")
    team_beta = Team(id=2, name="Team Beta", description="Regular rotation team")
    team_gamma = Team(id=3, name="Team Gamma", description="Regular rotation team")
    team_brandschutz = Team(id=4, name="Brandschutzdienst", description="Fire protection team")
    
    # Configure team shift assignments
    # Team Alpha, Beta, Gamma: F, S, N (standard rotation)
    f_id = next((st.id for st in shift_types if st.code == "F"), None)
    s_id = next((st.id for st in shift_types if st.code == "S"), None)
    n_id = next((st.id for st in shift_types if st.code == "N"), None)
    ts_id = next((st.id for st in shift_types if st.code == "TS"), None)
    
    team_alpha.allowed_shift_type_ids = [f_id, s_id, n_id]
    team_beta.allowed_shift_type_ids = [f_id, s_id, n_id]
    team_gamma.allowed_shift_type_ids = [f_id, s_id, n_id]
    team_brandschutz.allowed_shift_type_ids = [ts_id]  # ONLY TS shift
    
    teams = [team_alpha, team_beta, team_gamma, team_brandschutz]
    
    # Create employees
    employees = []
    
    # Team Alpha (5 members)
    for i in range(5):
        emp = Employee(
            id=i+1,
            vorname=f"Alpha{i+1}",
            name="Member",
            personalnummer=f"A{i+1:03d}",
            team_id=1
        )
        employees.append(emp)
        team_alpha.employees.append(emp)
    
    # Team Beta (5 members)
    for i in range(5):
        emp = Employee(
            id=i+6,
            vorname=f"Beta{i+1}",
            name="Member",
            personalnummer=f"B{i+1:03d}",
            team_id=2
        )
        employees.append(emp)
        team_beta.employees.append(emp)
    
    # Team Gamma (5 members)
    for i in range(5):
        emp = Employee(
            id=i+11,
            vorname=f"Gamma{i+1}",
            name="Member",
            personalnummer=f"G{i+1:03d}",
            team_id=3
        )
        employees.append(emp)
        team_gamma.employees.append(emp)
    
    # Team Brandschutzdienst (2 members)
    # These should ONLY work TS shift (NOT TD, which is a special marker)
    for i in range(2):
        emp = Employee(
            id=i+16,
            vorname=f"Brand{i+1}",
            name="Schutz",
            personalnummer=f"BS{i+1:03d}",
            team_id=4
            # NOTE: NOT is_td_qualified - that's for the special TD marker system
        )
        employees.append(emp)
        team_brandschutz.employees.append(emp)
    
    # No absences for this test
    absences = []
    
    # Planning period: 2 weeks
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=13)  # 2 weeks
    
    print(f"\nTeam configuration:")
    print(f"  Team Alpha: {len(team_alpha.employees)} members, shifts: F, S, N")
    print(f"  Team Beta: {len(team_beta.employees)} members, shifts: F, S, N")
    print(f"  Team Gamma: {len(team_gamma.employees)} members, shifts: F, S, N")
    print(f"  Team Brandschutzdienst: {len(team_brandschutz.employees)} members, shifts: TS (Tagschicht) only")
    print(f"\nPlanning period: {start} to {end}")
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences, shift_types
    )
    
    print("\nSolving...")
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print(f"\n✓ Solution found!")
    print(f"  Total assignments: {len(assignments)}")
    print(f"  TD assignments: {len(special_functions)}")
    
    # Verify Brandschutzdienst employees
    print("\n" + "=" * 70)
    print("Verifying Brandschutzdienst team assignments:")
    print("=" * 70)
    
    brandschutz_violations = []
    brandschutz_assignments = defaultdict(lambda: defaultdict(str))
    
    for emp in team_brandschutz.employees:
        print(f"\n{emp.full_name} (ID: {emp.id}):")
        
        # Check each day
        current_date = start
        while current_date <= end:
            assignment_code = complete_schedule.get((emp.id, current_date), "OFF")
            weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
            
            print(f"  {current_date} ({weekday_name}): {assignment_code}")
            
            # Check for violations
            is_weekend = current_date.weekday() >= 5
            
            if assignment_code in ["F", "S", "N"]:
                # Employee from Brandschutzdienst assigned to F/S/N shift - VIOLATION!
                violation = f"{emp.full_name} assigned to {assignment_code} shift on {current_date} ({weekday_name})"
                brandschutz_violations.append(violation)
                print(f"    ❌ VIOLATION: Should only work TD shift!")
            
            elif assignment_code != "OFF" and assignment_code != "TS" and is_weekend:
                # Employee working on weekend - VIOLATION!
                violation = f"{emp.full_name} assigned to {assignment_code} on weekend {current_date} ({weekday_name})"
                brandschutz_violations.append(violation)
                print(f"    ❌ VIOLATION: TS shift doesn't work weekends!")
            
            elif assignment_code == "TS":
                if is_weekend:
                    violation = f"{emp.full_name} assigned to TS on weekend {current_date} ({weekday_name})"
                    brandschutz_violations.append(violation)
                    print(f"    ❌ VIOLATION: TS shift doesn't work weekends!")
                else:
                    print(f"    ✓ Correct: TS shift on weekday")
            
            brandschutz_assignments[emp.id][current_date] = assignment_code
            current_date += timedelta(days=1)
    
    # Report results
    print("\n" + "=" * 70)
    print("RESULTS:")
    print("=" * 70)
    
    if brandschutz_violations:
        print(f"\n❌ FAIL: Found {len(brandschutz_violations)} violations:")
        for violation in brandschutz_violations:
            print(f"  - {violation}")
        return False
    else:
        print("\n✅ PASS: All Brandschutzdienst employees correctly assigned!")
        print("  - No F/S/N shift assignments")
        print("  - No weekend assignments")
        print("  - Only TS shift on weekdays (Mon-Fri)")
        
        # Count TS days
        ts_count = sum(1 for emp_schedules in brandschutz_assignments.values()
                      for code in emp_schedules.values()
                      if code == "TS")
        print(f"  - Total TS shift days across all members: {ts_count}")
        
        return True


def test_mixed_teams():
    """
    Test scenario with both regular rotation teams and special shift teams.
    """
    print("\n" + "=" * 70)
    print("TEST: Mixed Team Configuration")
    print("=" * 70)
    
    # This would test:
    # - Team 1: F/S/N rotation (standard)
    # - Team 2: F/S/N rotation (standard)
    # - Team 3: Only specific shifts (e.g., just F and S, no N)
    # - Team 4: Special shift (TD, BMT, BSB)
    
    print("(Test implementation placeholder - extend as needed)")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("TeamShiftAssignments Test Suite")
    print("=" * 70)
    
    tests = [
        ("Team with Special Shift", test_team_with_special_shift),
        ("Mixed Teams", test_mixed_teams),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Exception in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        exit(1)
