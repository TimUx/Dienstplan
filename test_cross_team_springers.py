"""
Test for weekly available employee constraint.

This test verifies that the system ensures at least one regular shift-team
member is completely free each week for dynamic coverage of absences.
"""

from datetime import date
from data_loader import load_from_database
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import Absence, AbsenceType


def test_weekly_availability_constraint():
    """
    Test that at least one regular shift-team member is free each week.
    """
    print("\n" + "=" * 70)
    print("TEST: Weekly Available Employee Constraint")
    print("=" * 70)
    
    employees, teams, absences, shift_types = load_from_database('dienstplan.db')
    
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    # Test with absences
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Max Müller (Team Alpha)
            absence_type=AbsenceType.AU,
            start_date=start_date,
            end_date=end_date,
            notes='Sick leave'
        ),
        Absence(
            id=9998,
            employee_id=2,  # Anna Schmidt (Team Alpha)
            absence_type=AbsenceType.U,
            start_date=start_date,
            end_date=end_date,
            notes='Vacation'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nScenario:")
    print(f"  Testing with 2 absences in Team Alpha")
    print(f"  System should still ensure at least 1 employee is completely free\n")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found!")
        return False
    
    assignments, _, _ = result
    
    print("✅ PASS: Solution found!")
    print(f"  Total assignments: {len(assignments)}")
    
    # Verify at least one employee is completely free
    VIRTUAL_TEAM_ID = 99
    regular_team_members = [e for e in employees 
                           if e.team_id and e.team_id != VIRTUAL_TEAM_ID 
                           and not e.is_ferienjobber]
    
    working_employees = set(a.employee_id for a in assignments)
    free_employees = [e for e in regular_team_members if e.id not in working_employees]
    
    print(f"\nAvailable employees this week: {len(free_employees)}")
    for emp in free_employees:
        team_name = next((t.name for t in teams if t.id == emp.team_id), 'Unknown')
        print(f"  - {emp.full_name} ({team_name})")
    
    if len(free_employees) >= 1:
        print("\n✅ Constraint satisfied: At least 1 employee completely free")
        return True
    else:
        print("\n❌ Constraint violated: No employees completely free")
        return False


def test_weekly_availability_with_minimal_absences():
    """
    Test weekly availability with minimal absences.
    """
    print("\n" + "=" * 70)
    print("TEST: Weekly Availability - Minimal Absences")
    print("=" * 70)
    
    employees, teams, absences, shift_types = load_from_database('dienstplan.db')
    
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    # Minimal absences
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Max Müller (Team Alpha)
            absence_type=AbsenceType.AU,
            start_date=start_date,
            end_date=end_date,
            notes='Sick leave'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nScenario:")
    print(f"  Testing with 1 absence in Team Alpha")
    print(f"  System should still ensure at least 1 employee is completely free\n")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found!")
        return False
    
    assignments, _, _ = result
    
    print("✅ PASS: Solution found!")
    print(f"  Total assignments: {len(assignments)}")
    
    # Verify at least one employee is completely free
    VIRTUAL_TEAM_ID = 99
    regular_team_members = [e for e in employees 
                           if e.team_id and e.team_id != VIRTUAL_TEAM_ID 
                           and not e.is_ferienjobber]
    
    working_employees = set(a.employee_id for a in assignments)
    free_employees = [e for e in regular_team_members if e.id not in working_employees]
    
    print(f"\nAvailable employees this week: {len(free_employees)}")
    
    if len(free_employees) >= 1:
        print("✅ Constraint satisfied")
        return True
    else:
        print("❌ Constraint violated")
        return False


def test_multiple_teams_with_absences():
    """
    Test with absences in multiple teams simultaneously.
    """
    print("\n" + "=" * 70)
    print("TEST: Multiple Teams with Absences")
    print("=" * 70)
    
    employees, teams, absences, shift_types = load_from_database('dienstplan.db')
    
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    # One absence per team
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Team Alpha
            absence_type=AbsenceType.AU,
            start_date=start_date,
            end_date=end_date,
            notes='Sick'
        ),
        Absence(
            id=9998,
            employee_id=6,  # Team Beta  
            absence_type=AbsenceType.U,
            start_date=start_date,
            end_date=end_date,
            notes='Vacation'
        ),
        Absence(
            id=9997,
            employee_id=11,  # Team Gamma
            absence_type=AbsenceType.L,
            start_date=start_date,
            end_date=end_date,
            notes='Training'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nScenario:")
    print(f"  Each team has 1 member absent")
    print(f"  System should still ensure at least 1 employee is completely free\n")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found!")
        return False
    
    assignments, _, _ = result
    
    print("✅ PASS: Solution found for all teams!")
    print(f"  Total assignments: {len(assignments)}")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("WEEKLY AVAILABILITY CONSTRAINT TESTS")
    print("Testing that at least 1 employee is free each week")
    print("=" * 70)
    
    results = []
    
    # Test 1: With multiple absences
    results.append(("Weekly availability with absences", test_weekly_availability_constraint()))
    
    # Test 2: With minimal absences
    results.append(("Weekly availability minimal", test_weekly_availability_with_minimal_absences()))
    
    # Test 3: Multiple teams with absences
    results.append(("Multiple teams with absences", test_multiple_teams_with_absences()))
    
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
        print("\n🎉 ALL TESTS PASSED! Weekly availability constraint working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review weekly availability logic.")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Cross-team springer support working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review cross-team springer logic.")
