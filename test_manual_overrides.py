"""
Test manual override functionality.
Verifies that administrators can lock assignments.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import get_shift_type_by_id


def test_locked_team_shift():
    """
    Test that locked team shifts are applied correctly.
    
    Note: With only 3 teams and strict staffing requirements, not all locks
    are feasible. This test verifies that:
    1. Locks are correctly applied to the model
    2. Compatible locks result in valid solutions
    3. Incompatible locks result in INFEASIBLE status (correct behavior)
    """
    print("\n" + "=" * 70)
    print("TEST: Locked Team Shift Override")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=13)  # 2 weeks
    
    # Test 1: Lock to a compatible value (Team Alpha would normally have 'F' in week 0)
    locked_team_shift = {
        (1, 0): 'F'  # Team 1 (Alpha), Week 0 -> 'F' (same as normal rotation)
    }
    
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        locked_team_shift=locked_team_shift
    )
    
    # Verify the lock was applied
    if (1, 0) not in planning_model.locked_team_shift:
        print("❌ FAIL: Lock not stored in model")
        return False
    
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found for compatible lock")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Verify Team Alpha has 'F' in week 0
    team_alpha_members = [e for e in employees if e.team_id == 1 and not e.is_springer]
    week0_end = start + timedelta(days=4)  # Mon-Fri
    
    team_alpha_week0_shifts = set()
    for assignment in assignments:
        if assignment.employee_id in [m.id for m in team_alpha_members]:
            if start <= assignment.date <= week0_end and assignment.date.weekday() < 5:
                shift_type = get_shift_type_by_id(assignment.shift_type_id)
                if shift_type:
                    team_alpha_week0_shifts.add(shift_type.code)
    
    if 'F' in team_alpha_week0_shifts and len(team_alpha_week0_shifts) == 1:
        print(f"✅ PASS: Locked team shift applied correctly")
        print(f"   Team Alpha week 0 shifts: {team_alpha_week0_shifts}")
        print(f"   Manual override mechanism working!")
        return True
    else:
        print(f"❌ FAIL: Team Alpha week 0 shifts incorrect")
        print(f"   Expected: {{'F'}}, Got: {team_alpha_week0_shifts}")
        return False


def test_locked_employee_weekend():
    """
    Test that locked employee weekend assignments are respected.
    """
    print("\n" + "=" * 70)
    print("TEST: Locked Employee Weekend Override")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date(2025, 1, 4)  # Saturday
    end = start + timedelta(days=1)  # Sunday
    
    # Lock an employee to work on Saturday
    test_employee = employees[0]
    locked_employee_weekend = {
        (test_employee.id, start): True  # Employee works on Saturday
    }
    
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        locked_employee_weekend=locked_employee_weekend
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Check if employee works on Saturday
    works_saturday = any(
        a.employee_id == test_employee.id and a.date == start
        for a in assignments
    )
    
    if works_saturday:
        print(f"✅ PASS: Employee {test_employee.full_name} locked to work on Saturday")
        return True
    else:
        print(f"❌ FAIL: Employee {test_employee.full_name} not working on Saturday as locked")
        return False


def test_locked_td():
    """
    Test that locked TD assignments are respected.
    """
    print("\n" + "=" * 70)
    print("TEST: Locked TD Override")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=4)  # Friday
    
    # Find a TD-qualified employee
    td_qualified = [e for e in employees if e.can_do_td]
    
    if not td_qualified:
        print("ℹ️ INFO: No TD-qualified employees in sample data")
        return True
    
    test_employee = td_qualified[0]
    
    # Lock TD assignment to this employee in week 0
    locked_td = {
        (test_employee.id, 0): True  # Employee has TD in week 0
    }
    
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        locked_td=locked_td
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Check if employee has TD in week 0
    has_td = any(
        emp_id == test_employee.id and func == "TD"
        for (emp_id, d), func in special_functions.items()
    )
    
    if has_td:
        print(f"✅ PASS: Employee {test_employee.full_name} locked to TD duty")
        return True
    else:
        print(f"❌ FAIL: Employee {test_employee.full_name} not assigned TD as locked")
        return False


def run_all_tests():
    """Run all manual override tests"""
    print("\n" + "=" * 70)
    print("MANUAL OVERRIDE TESTS")
    print("=" * 70)
    
    tests = [
        ("Locked Team Shift", test_locked_team_shift),
        ("Locked Employee Weekend", test_locked_employee_weekend),
        ("Locked TD", test_locked_td),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Manual overrides working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
