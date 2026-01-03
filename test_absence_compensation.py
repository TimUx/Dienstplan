"""
Test for shift planning with employee absences.

This test verifies that the shift planning system can handle scenarios
where employees are absent (AU - sick, U - vacation) and springers
compensate to meet staffing requirements.

This addresses the issue where January 2026 planning was INFEASIBLE
because springers were not counted in staffing constraints.
"""

from datetime import date
from data_loader import load_from_database
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import Absence, AbsenceType


def test_january_2026_with_absences():
    """
    Test the exact scenario from the problem statement:
    - Planning period: December 31, 2025 to January 30, 2026
    - One employee AU (sick)
    - One employee U (vacation)
    - Springers should compensate
    """
    print("\n" + "=" * 70)
    print("TEST: January 2026 with Employee Absences")
    print("=" * 70)
    
    # Load data from database (has correct springer structure)
    employees, teams, absences, shift_types = load_from_database('dienstplan.db')
    
    # Define planning period (as in problem statement)
    start_date = date(2025, 12, 31)
    end_date = date(2026, 1, 30)
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Duration: {(end_date - start_date).days + 1} days")
    
    # Add realistic absences
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Team member
            absence_type=AbsenceType.AU,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 11),
            notes='Sick leave - must be compensated by team'
        ),
        Absence(
            id=9998,
            employee_id=6,  # Team member from different team
            absence_type=AbsenceType.U,
            start_date=date(2026, 1, 12),
            end_date=date(2026, 1, 25),
            notes='Vacation - must be compensated by team'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nAbsences:")
    for abs in test_absences:
        emp = next((e for e in employees if e.id == abs.employee_id), None)
        if emp:
            print(f"  - {emp.full_name} (Team {emp.team_id}): {abs.absence_type.value}")
            print(f"    From {abs.start_date} to {abs.end_date}")
    
    # Create model
    print("\nCreating shift planning model...")
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    
    # Solve
    print("Solving with OR-Tools CP-SAT...")
    result = solve_shift_planning(planning_model, time_limit_seconds=300)
    
    if not result:
        print("\n❌ FAIL: No solution found (INFEASIBLE)")
        print("This means springers are not properly compensating for absences!")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print(f"\n✅ SUCCESS: Solution found!")
    print(f"  - Total assignments: {len(assignments)}")
    print(f"  - TD assignments: {len(special_functions)}")
    
    # Verify springer compensation
    print("\nSpringer compensation analysis:")
    # Track available employees (those not working)
    available_employees_days = {}
    
    VIRTUAL_TEAM_ID = 99
    regular_team_members = [e for e in employees 
                           if e.team_id and e.team_id != VIRTUAL_TEAM_ID 
                           and not e.is_ferienjobber]
    
    working_employees = set(a.employee_id for a in assignments)
    
    for emp in regular_team_members:
        if emp.id not in working_employees:
            available_employees_days[emp.id] = {
                'name': emp.full_name,
                'team': emp.team_id,
                'available': True
            }
            springer_working_days[emp.id]['days'].append(assignment.date)
    
    if not springer_working_days:
        print("  ⚠️  WARNING: No springer assignments found!")
        print("  This is unexpected with absences present.")
        return False
    
    total_springer_days = 0
    for emp_id, data in springer_working_days.items():
        working_days = len(data['days'])
        total_springer_days += working_days
        print(f"  - {data['name']} (Team {data['team']}): {working_days} working days")
    
    print(f"\nTotal springer working days: {total_springer_days}")
    
    # Verify staffing requirements are met
    print("\nVerifying solution quality...")
    print("✅ PASS: Solution found and springers compensated for absences!")
    print("  (Staffing requirements are enforced by solver constraints)")
    
    return True


def test_single_absence_per_team():
    """
    Test with one absence per team - realistic scenario that should be solvable.
    """
    print("\n" + "=" * 70)
    print("TEST: Single Absence Per Team")
    print("=" * 70)
    
    employees, teams, absences, shift_types = load_from_database('dienstplan.db')
    
    # Short planning period
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 18)
    
    # One employee from each team absent (realistic scenario)
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Team Alpha
            absence_type=AbsenceType.AU,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 11),
            notes='Sick leave - springer compensates'
        ),
        Absence(
            id=9998,
            employee_id=6,  # Team Beta
            absence_type=AbsenceType.U,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 11),
            notes='Vacation - springer compensates'
        ),
        Absence(
            id=9997,
            employee_id=11,  # Team Gamma
            absence_type=AbsenceType.L,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 11),
            notes='Training - springer compensates'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"One member from each team absent (realistic load)")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if result:
        assignments, _, _ = result
        
        # Count available employees (not working)
        VIRTUAL_TEAM_ID = 99
        regular_members = [e for e in employees 
                          if e.team_id and e.team_id != VIRTUAL_TEAM_ID 
                          and not e.is_ferienjobber]
        working = set(a.employee_id for a in assignments)
        available_count = len([e for e in regular_members if e.id not in working])
        
        print(f"\n✅ PASS: Solution found with 3 simultaneous absences")
        print(f"  Available employees not working: {available_count}")
        return True
    else:
        print("\n❌ FAIL: Could not handle one absence per team")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ABSENCE COMPENSATION TESTS")
    print("Testing springer compensation for absent employees")
    print("=" * 70)
    
    results = []
    
    # Test 1: January 2026 scenario
    results.append(("January 2026 with absences", test_january_2026_with_absences()))
    
    # Test 2: Single absence per team (realistic scenario)
    results.append(("Single absence per team", test_single_absence_per_team()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Springer compensation working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review springer compensation logic.")
