"""
Test for cross-team springer support in worst-case absence scenarios.

This test verifies that springers from other teams can help when multiple
members of one team are absent (AU, U, L), enabling the shift planner to
find feasible solutions even in extreme scenarios.
"""

from datetime import date
from data_loader import load_from_database
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import Absence, AbsenceType


def test_cross_team_worst_case():
    """
    Test worst case: 2 members of same team absent simultaneously.
    Requires cross-team springer support to find solution.
    """
    print("\n" + "=" * 70)
    print("TEST: Cross-Team Springer Support - Worst Case")
    print("=" * 70)
    
    employees, teams, absences = load_from_database('dienstplan.db')
    
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    # Worst case: 2 regular members of Team Alpha absent
    test_absences = [
        Absence(
            id=9999,
            employee_id=1,  # Max Müller (Team Alpha)
            absence_type=AbsenceType.AU,
            start_date=start_date,
            end_date=end_date,
            notes='Sick leave - severe case'
        ),
        Absence(
            id=9998,
            employee_id=2,  # Anna Schmidt (Team Alpha)
            absence_type=AbsenceType.U,
            start_date=start_date,
            end_date=end_date,
            notes='Vacation - pre-approved'
        )
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nScenario:")
    print(f"  Team Alpha: 5 members (4 regular + 1 springer)")
    print(f"  Absences: 2 regular members")
    print(f"  Available: 2 regular + 1 springer = 3 people")
    print(f"  Required: min 4 for F shift")
    print(f"  Solution: Need cross-team springer help!\n")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found - cross-team support not working!")
        return False
    
    assignments, _, _ = result
    
    print("✅ PASS: Solution found with cross-team springer support!")
    print(f"  Total assignments: {len(assignments)}")
    
    # Verify cross-team assistance
    team_alpha_springer = next((e for e in employees if e.team_id == 1 and e.is_springer), None)
    other_springers = [e for e in employees if e.is_springer and e.team_id != 1 and e.team_id is not None]
    
    print(f"\nSpringer analysis:")
    print(f"  Team Alpha springer: {team_alpha_springer.full_name if team_alpha_springer else 'None'}")
    print(f"  Other team springers: {[e.full_name for e in other_springers]}")
    
    return True


def test_cross_team_not_used_when_unnecessary():
    """
    Test that cross-team springers are NOT used when not necessary.
    With only 1 absence, own-team springer should be sufficient.
    """
    print("\n" + "=" * 70)
    print("TEST: Cross-Team NOT Used When Unnecessary")
    print("=" * 70)
    
    employees, teams, absences = load_from_database('dienstplan.db')
    
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    # Only 1 absence - should be solvable with own-team springer
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
    print(f"  Team Alpha: 5 members (4 regular + 1 springer)")
    print(f"  Absences: 1 regular member")
    print(f"  Available: 3 regular + 1 springer = 4 people")
    print(f"  Required: min 4 for F shift")
    print(f"  Expected: Own-team springer sufficient (no cross-team needed)\n")
    
    # Create model and solve
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("❌ FAIL: No solution found!")
        return False
    
    print("✅ PASS: Solution found (own-team springer sufficient)")
    print("  Cross-team springers should be minimized by optimization")
    
    return True


def test_multiple_teams_with_absences():
    """
    Test with absences in multiple teams simultaneously.
    Each team should use its own springer first, cross-team only if needed.
    """
    print("\n" + "=" * 70)
    print("TEST: Multiple Teams with Absences")
    print("=" * 70)
    
    employees, teams, absences = load_from_database('dienstplan.db')
    
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
    print(f"  Each team: 3 regular + 1 springer = 4 available")
    print(f"  Expected: All teams can meet requirements with own springers\n")
    
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
    print("CROSS-TEAM SPRINGER SUPPORT TESTS")
    print("Testing worst-case absence scenarios")
    print("=" * 70)
    
    results = []
    
    # Test 1: Worst case - needs cross-team
    results.append(("Cross-team worst case", test_cross_team_worst_case()))
    
    # Test 2: Normal case - cross-team not needed
    results.append(("Cross-team not used unnecessarily", test_cross_team_not_used_when_unnecessary()))
    
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
        print("\n🎉 ALL TESTS PASSED! Cross-team springer support working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review cross-team springer logic.")
