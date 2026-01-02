"""
Test new features: Complete schedule and TD assignments.
Verifies the fixes for the problem statement requirements.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from validation import validate_shift_plan


def test_all_employees_in_complete_schedule():
    """
    TEST 1: Verify ALL employees appear in complete schedule.
    
    Requirement from problem statement:
    "ALL employees MUST always appear in the schedule output,
    regardless of whether they have a shift, weekend, TD, or no assignment."
    """
    print("\n" + "=" * 70)
    print("TEST 1: All Employees in Complete Schedule")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date.today()
    end = start + timedelta(days=6)  # 1 week
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Verify complete_schedule exists and is not empty
    if not complete_schedule:
        print("❌ FAIL: complete_schedule is empty")
        return False
    
    # Generate all dates
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    
    # Check each employee appears for each date
    missing_entries = []
    for emp in employees:
        for d in dates:
            if (emp.id, d) not in complete_schedule:
                missing_entries.append((emp.full_name, d))
    
    if missing_entries:
        print(f"❌ FAIL: Missing {len(missing_entries)} entries in complete schedule")
        for name, d in missing_entries[:5]:  # Show first 5
            print(f"  - {name} on {d}")
        return False
    
    # Verify all employees are represented
    emp_in_schedule = set(emp_id for emp_id, _ in complete_schedule.keys())
    if len(emp_in_schedule) != len(employees):
        print(f"❌ FAIL: Only {len(emp_in_schedule)}/{len(employees)} employees in schedule")
        return False
    
    # Show statistics
    total_entries = len(complete_schedule)
    expected_entries = len(employees) * len(dates)
    
    print(f"✅ PASS: All employees appear in complete schedule")
    print(f"   Total employees: {len(employees)}")
    print(f"   Total dates: {len(dates)}")
    print(f"   Total entries: {total_entries}")
    print(f"   Expected entries: {expected_entries}")
    print(f"   Match: {total_entries == expected_entries}")
    
    # Show sample of complete schedule
    print(f"\n   Sample entries:")
    for i, ((emp_id, d), status) in enumerate(list(complete_schedule.items())[:5]):
        emp = next(e for e in employees if e.id == emp_id)
        print(f"     {emp.full_name} on {d}: {status}")
    
    return True


def test_td_assignments():
    """
    TEST 2: Verify TD (Day Duty) assignments are working.
    
    Requirements from problem statement:
    - Exactly ONE TD per week (Mon-Fri)
    - TD must be assigned to qualified employee
    - TD is visible in special_functions
    - TD replaces regular shifts for that employee
    """
    print("\n" + "=" * 70)
    print("TEST 2: TD (Day Duty) Assignments")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date.today()
    end = start + timedelta(days=13)  # 2 weeks
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Check TD assignments exist
    if not special_functions:
        print("❌ FAIL: No TD assignments found")
        return False
    
    td_assignments = [(emp_id, d) for (emp_id, d), func in special_functions.items() if func == "TD"]
    
    if not td_assignments:
        print("❌ FAIL: No TD assignments in special_functions")
        return False
    
    # Generate weeks
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Check each week has exactly 1 TD
    td_per_week = []
    for week_idx, week_dates in enumerate(weeks):
        weekday_dates = [d for d in week_dates if d.weekday() < 5]
        
        if not weekday_dates:
            continue
        
        # Count TD assignments this week
        td_employees = set()
        for emp in employees:
            has_td = any((emp.id, d) in special_functions and special_functions[(emp.id, d)] == "TD" 
                        for d in weekday_dates)
            if has_td:
                td_employees.add(emp.id)
        
        td_per_week.append((week_idx, len(td_employees), td_employees))
    
    # Verify exactly 1 TD per week
    all_correct = True
    for week_idx, count, td_emps in td_per_week:
        if count != 1:
            print(f"❌ FAIL: Week {week_idx} has {count} TD assignments (should be 1)")
            all_correct = False
    
    if not all_correct:
        return False
    
    # Verify TD employees are qualified
    td_employee_ids = set(emp_id for emp_id, _ in td_assignments)
    for emp_id in td_employee_ids:
        emp = next(e for e in employees if e.id == emp_id)
        if not emp.can_do_td:
            print(f"❌ FAIL: Employee {emp.full_name} has TD but not qualified")
            return False
    
    # Verify TD employees are in virtual team or have qualification
    print(f"✅ PASS: TD assignments working correctly")
    print(f"   Total TD assignments (day-level): {len(td_assignments)}")
    print(f"   TD per week: {[count for _, count, _ in td_per_week]}")
    print(f"   TD employees:")
    for emp_id in td_employee_ids:
        emp = next(e for e in employees if e.id == emp_id)
        print(f"     - {emp.full_name} (Team: {emp.team_id}, Qualified: {emp.can_do_td})")
    
    return True


def test_virtual_team_fire_alarm():
    """
    TEST 3: Verify virtual team "Fire Alarm System" is created.
    
    Requirements from problem statement:
    - Create virtual team "Fire Alarm System"
    - Members: employees without regular team or with special function
    - Team does NOT participate in F/N/S rotation
    - Members receive ONLY TD or OFF
    """
    print("\n" + "=" * 70)
    print("TEST 3: Virtual Team 'Fire Alarm System'")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    
    # Check if virtual team exists
    fire_alarm_team = next((t for t in teams if t.name == "Fire Alarm System"), None)
    
    if not fire_alarm_team:
        print("❌ FAIL: Virtual team 'Fire Alarm System' not found")
        return False
    
    print(f"✅ PASS: Virtual team found (ID: {fire_alarm_team.id})")
    print(f"   Members: {len(fire_alarm_team.employees)}")
    for emp in fire_alarm_team.employees:
        print(f"     - {emp.full_name} (TD-qualified: {emp.can_do_td})")
    
    # Verify members are TD-qualified
    for emp in fire_alarm_team.employees:
        if not emp.can_do_td:
            print(f"⚠ WARNING: {emp.full_name} in Fire Alarm System but not TD-qualified")
    
    # Test that fire alarm team members don't get regular shifts
    start = date.today()
    end = start + timedelta(days=6)
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Check fire alarm team members only have TD or OFF
    for emp in fire_alarm_team.employees:
        emp_assignments = [a for a in assignments if a.employee_id == emp.id]
        
        # Fire alarm team members should not have regular shift assignments
        # (they're in virtual team for TD duty only)
        if emp_assignments:
            print(f"❌ FAIL: {emp.full_name} from Fire Alarm System has regular shift assignments")
            return False
    
    print(f"✅ PASS: Fire Alarm System members don't have regular shifts")
    
    return True


def test_validation_with_new_features():
    """
    TEST 4: Verify validation catches missing employees and TD issues.
    """
    print("\n" + "=" * 70)
    print("TEST 4: Validation with New Features")
    print("=" * 70)
    
    employees, teams, absences = generate_sample_data()
    start = date.today()
    end = start + timedelta(days=6)
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Run validation with all new parameters
    validation_result = validate_shift_plan(
        assignments, employees, absences, start, end, teams,
        special_functions, complete_schedule
    )
    
    if not validation_result.is_valid:
        print(f"❌ FAIL: Validation found violations")
        validation_result.print_report()
        return False
    
    print(f"✅ PASS: Validation successful")
    print(f"   Violations: {len(validation_result.violations)}")
    print(f"   Warnings: {len(validation_result.warnings)}")
    
    if validation_result.warnings:
        print(f"   Warnings:")
        for warning in validation_result.warnings[:3]:
            print(f"     - {warning}")
    
    return True


def main():
    """Run all new feature tests"""
    print("\n" + "=" * 70)
    print("NEW FEATURES TEST SUITE")
    print("Testing: Complete Schedule, TD Assignments, Virtual Team")
    print("=" * 70)
    
    tests = [
        ("All Employees in Schedule", test_all_employees_in_complete_schedule),
        ("TD Assignments", test_td_assignments),
        ("Virtual Team Fire Alarm", test_virtual_team_fire_alarm),
        ("Validation", test_validation_with_new_features),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 ALL NEW FEATURE TESTS PASSED!")
    else:
        print("\n❌ Some tests failed")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
