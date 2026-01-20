"""
Test to verify that no employee is assigned two shifts on the same day.

This test addresses the problem statement:
"Aktuell werden zum Teil einem Benutzer an einem Tag zwei Schichten geplant."
(Currently, sometimes a user is assigned two shifts on one day.)

The fix ensures that the "at most one shift per day" constraint applies to:
- Weekdays (Monday-Friday) - already existed
- Weekends (Saturday-Sunday) - NEW FIX
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import get_shift_type_by_id, STANDARD_SHIFT_TYPES, ShiftType
from collections import defaultdict

def test_no_double_shifts():
    """
    Test that no employee is assigned multiple shifts on the same day.
    
    This is a CRITICAL constraint - employees must have at most ONE shift per day,
    regardless of whether it's a weekday or weekend.
    """
    print("\n" + "=" * 80)
    print("TEST: No Double Shifts Per Day (Weekdays AND Weekends)")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Use 4 weeks for testing (includes weekdays and weekends)
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=27)  # 4 weeks (28 days)
    
    # Configure shifts to 48h/week
    # This configuration requires employees to work 6 days per week (48h ÷ 8h/day = 6 days)
    # which encourages cross-team assignments to help meet the higher weekly hour requirement
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    print(f"\nPlanning period: {start} to {end} (4 weeks)")
    print(f"Checking that no employee has multiple shifts on the same day...")
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        shift_types=shift_types_48h
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=90)
    
    if not result:
        print("\n❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print(f"\n✓ Solution found with {len(assignments)} shift assignments")
    
    # Group assignments by employee and date
    assignments_by_emp_date = defaultdict(list)
    for assignment in assignments:
        key = (assignment.employee_id, assignment.date)
        assignments_by_emp_date[key].append(assignment)
    
    # Check for double shifts
    print("\n" + "-" * 80)
    print("CHECKING FOR DOUBLE SHIFTS")
    print("-" * 80)
    
    violations = []
    weekday_doubles = 0
    weekend_doubles = 0
    
    for (emp_id, d), shift_list in assignments_by_emp_date.items():
        if len(shift_list) > 1:
            # Find employee
            emp = next((e for e in employees if e.id == emp_id), None)
            emp_name = emp.full_name if emp else f"Employee {emp_id}"
            
            # Get shift codes
            shift_codes = []
            for assignment in shift_list:
                shift_type = get_shift_type_by_id(assignment.shift_type_id)
                if shift_type:
                    shift_codes.append(shift_type.code)
            
            is_weekend = d.weekday() >= 5
            day_type = "WEEKEND" if is_weekend else "WEEKDAY"
            
            violation = (
                f"❌ {day_type} VIOLATION: {emp_name} has {len(shift_list)} shifts on {d} "
                f"({d.strftime('%A')}): {', '.join(shift_codes)}"
            )
            violations.append(violation)
            
            if is_weekend:
                weekend_doubles += 1
            else:
                weekday_doubles += 1
    
    # Print results
    if violations:
        print(f"\n⚠️  FOUND {len(violations)} DOUBLE SHIFT VIOLATIONS:")
        for violation in violations:
            print(f"  {violation}")
        
        print(f"\nBreakdown:")
        print(f"  - Weekday double shifts: {weekday_doubles}")
        print(f"  - Weekend double shifts: {weekend_doubles}")
        
        print("\n❌ TEST FAILED: Employees have multiple shifts on the same day!")
        return False
    else:
        print("\n✅ SUCCESS: No employee has multiple shifts on the same day!")
        print(f"  - Checked {len(assignments_by_emp_date)} employee-day combinations")
        print(f"  - All employees have at most 1 shift per day")
        return True


def test_weekend_double_shifts_prevented():
    """
    Specific test for weekend double shifts.
    
    This test ensures the fix for the problem statement is working:
    Weekend employees should not be assigned both their team shift AND
    a cross-team shift on the same weekend day.
    """
    print("\n" + "=" * 80)
    print("TEST: Weekend Double Shifts Prevention (Specific)")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Use 2 weeks for focused testing
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=13)  # 2 weeks
    
    # Configure shifts to 48h/week
    # This configuration requires employees to work 6 days per week (48h ÷ 8h/day = 6 days)
    # which encourages cross-team assignments to help meet the higher weekly hour requirement
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    print(f"\nPlanning period: {start} to {end} (2 weeks)")
    print(f"Specifically checking weekend days (Saturday, Sunday)...")
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        shift_types=shift_types_48h
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("\n❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    # Filter to weekend assignments only
    weekend_assignments = [a for a in assignments if a.date.weekday() >= 5]
    
    print(f"\n✓ Solution found with {len(weekend_assignments)} weekend shift assignments")
    
    # Group weekend assignments by employee and date
    weekend_by_emp_date = defaultdict(list)
    for assignment in weekend_assignments:
        key = (assignment.employee_id, assignment.date)
        weekend_by_emp_date[key].append(assignment)
    
    # Check for double shifts on weekends
    weekend_violations = []
    
    for (emp_id, d), shift_list in weekend_by_emp_date.items():
        if len(shift_list) > 1:
            emp = next((e for e in employees if e.id == emp_id), None)
            emp_name = emp.full_name if emp else f"Employee {emp_id}"
            
            shift_codes = []
            for assignment in shift_list:
                shift_type = get_shift_type_by_id(assignment.shift_type_id)
                if shift_type:
                    shift_codes.append(shift_type.code)
            
            violation = (
                f"❌ {emp_name} has {len(shift_list)} shifts on {d} "
                f"({d.strftime('%A')}): {', '.join(shift_codes)}"
            )
            weekend_violations.append(violation)
    
    # Print results
    if weekend_violations:
        print(f"\n⚠️  FOUND {len(weekend_violations)} WEEKEND DOUBLE SHIFT VIOLATIONS:")
        for violation in weekend_violations:
            print(f"  {violation}")
        
        print("\n❌ TEST FAILED: Weekend double shifts not prevented!")
        return False
    else:
        print("\n✅ SUCCESS: No weekend double shifts found!")
        print(f"  - Checked {len(weekend_by_emp_date)} employee-weekend-day combinations")
        print(f"  - All employees have at most 1 shift per weekend day")
        return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("COMPREHENSIVE DOUBLE SHIFT PREVENTION TESTS")
    print("=" * 80)
    
    results = []
    
    # Test 1: General no double shifts (weekdays + weekends)
    results.append(("No double shifts (weekdays + weekends)", test_no_double_shifts()))
    
    # Test 2: Specific weekend double shift prevention
    results.append(("Weekend double shifts prevented", test_weekend_double_shifts_prevented()))
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS")
    print("=" * 80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Review implementation")
