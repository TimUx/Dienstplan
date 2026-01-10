"""
Test for minimum working hours constraint based on configured weekly_working_hours.

This test verifies the solution to the problem statement:
- Employees must work at least the configured weekly_working_hours
- Monthly hours = weekly_working_hours * 4 weeks
- Absences (U/AU/L) are exceptions - no compensation required
- If an employee works less in one week (without absence), they must compensate in other weeks
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import (
    get_shift_type_by_id, STANDARD_SHIFT_TYPES, ShiftType, 
    Absence, AbsenceType
)

def test_minimum_hours_with_48h_config():
    """
    Test that employees meet minimum working hours when shifts are configured to 48h/week.
    
    This replicates the example from the problem statement:
    - Shifts F, S, N configured to 48h/week
    - Expected: 192h/month (4 weeks × 48h)
    - Previously: ~152h/month (FAILED)
    - Now: Should achieve 192h/month (SUCCESS)
    """
    print("\n" + "=" * 80)
    print("TEST: Minimum Working Hours with 48h/week Configuration")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Configure shifts to 48h/week as per problem statement example
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    # Use 4 weeks for testing (1 month)
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=27)  # 4 weeks (28 days)
    
    print(f"\nPlanning period: {start} to {end} (4 weeks)")
    print(f"Shift configuration: F, S, N = 48h/week target")
    print(f"Expected monthly hours per employee: 192h (4 × 48h)")
    
    # Create and solve model with 48h configuration
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
    
    # Analyze working hours per employee
    print("\n" + "-" * 80)
    print("WORKING HOURS ANALYSIS")
    print("-" * 80)
    
    emp_hours = {}
    emp_days = {}
    emp_weekly_hours = {}
    
    for assignment in assignments:
        emp_id = assignment.employee_id
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        
        if emp_id not in emp_hours:
            emp_hours[emp_id] = 0
            emp_days[emp_id] = []
            emp_weekly_hours[emp_id] = {}
        
        emp_hours[emp_id] += shift_type.hours
        emp_days[emp_id].append(assignment.date)
        
        # Track weekly hours
        week_num = (assignment.date - start).days // 7
        if week_num not in emp_weekly_hours[emp_id]:
            emp_weekly_hours[emp_id][week_num] = 0
        emp_weekly_hours[emp_id][week_num] += shift_type.hours
    
    # Count employees with absences
    employees_with_absences = set()
    for absence in absences:
        if absence.start_date <= end and absence.end_date >= start:
            employees_with_absences.add(absence.employee_id)
    
    # Check results
    success = True
    employees_meeting_target = 0
    employees_below_target = 0
    employees_with_absence_exception = 0
    
    for emp in employees:
        if emp.id not in emp_hours:
            continue
        
        total_hours = emp_hours[emp.id]
        days_worked = len(emp_days[emp.id])
        avg_weekly = total_hours / 4  # 4 weeks
        
        # Get employee's team
        team = next((t for t in teams if t.id == emp.team_id), None)
        team_name = team.name if team else "No team"
        
        print(f"\n{emp.full_name} ({team_name}):")
        print(f"  Total hours: {total_hours}h / 4 weeks")
        print(f"  Days worked: {days_worked}")
        print(f"  Average: {avg_weekly:.1f}h/week")
        
        # Show weekly breakdown
        print(f"  Weekly breakdown:")
        for week_num in sorted(emp_weekly_hours[emp.id].keys()):
            hours = emp_weekly_hours[emp.id][week_num]
            print(f"    Week {week_num + 1}: {hours}h")
        
        # Check if employee has absence (exception to minimum hours)
        if emp.id in employees_with_absences:
            print(f"  ℹ️  Has absence - exempt from minimum hours requirement")
            employees_with_absence_exception += 1
        else:
            # Check if it meets expected 48h/week = 192h/month
            if total_hours >= 192:
                print(f"  ✓ Meets target of 192h/month (48h/week)")
                employees_meeting_target += 1
            else:
                shortfall = 192 - total_hours
                print(f"  ❌ SHORTFALL: {shortfall}h below expected 192h/month")
                employees_below_target += 1
                success = False
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Employees meeting 192h target: {employees_meeting_target}")
    print(f"Employees with absence (exempt): {employees_with_absence_exception}")
    print(f"Employees below target: {employees_below_target}")
    
    if success:
        print("\n✅ SUCCESS: All employees without absences meet the 192h/month target!")
        return True
    else:
        print("\n❌ FAILURE: Some employees still not meeting minimum hours")
        return False


def test_minimum_hours_with_40h_config():
    """
    Test that the solution works with different weekly_working_hours configurations.
    
    This tests with 40h/week configuration to ensure the solution is dynamic:
    - Shifts F, S, N configured to 40h/week
    - Expected: 160h/month (4 weeks × 40h)
    """
    print("\n" + "=" * 80)
    print("TEST: Minimum Working Hours with 40h/week Configuration")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Configure shifts to 40h/week (standard work week)
    shift_types_40h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 40.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 40.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 40.0),
    ]
    
    # Use 4 weeks for testing
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=27)  # 4 weeks
    
    print(f"\nPlanning period: {start} to {end} (4 weeks)")
    print(f"Shift configuration: F, S, N = 40h/week target")
    print(f"Expected monthly hours per employee: 160h (4 × 40h)")
    
    # Create and solve model with 40h configuration
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        shift_types=shift_types_40h
    )
    result = solve_shift_planning(planning_model, time_limit_seconds=90)
    
    if not result:
        print("\n❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    print(f"\n✓ Solution found with {len(assignments)} shift assignments")
    
    # Quick check: count total hours
    emp_hours = {}
    for assignment in assignments:
        emp_id = assignment.employee_id
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
    
    # Check if employees are working around 160h (allow small variance)
    employees_with_absences = set(abs.employee_id for abs in absences 
                                  if abs.start_date <= end and abs.end_date >= start)
    
    success = True
    for emp in employees:
        if emp.id not in emp_hours:
            continue
        if emp.id in employees_with_absences:
            continue  # Exempt from requirement
        
        total_hours = emp_hours[emp.id]
        if total_hours < 160:
            print(f"❌ {emp.full_name}: {total_hours}h < 160h target")
            success = False
    
    if success:
        print("\n✅ SUCCESS: Configuration with 40h/week works correctly!")
        return True
    else:
        print("\n❌ FAILURE: 40h/week configuration not met")
        return False


def test_absence_exemption():
    """
    Test that absences (U/AU/L) properly exempt employees from minimum hours.
    
    Verifies requirement: "Ausnahmen von der Regel je Mitarbeiter, sind Abwesenheiten"
    """
    print("\n" + "=" * 80)
    print("TEST: Absence Exemption from Minimum Hours")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, base_absences = generate_sample_data()
    
    # Add significant absences for testing
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=27)  # 4 weeks
    
    # Add 2-week vacation for employee 1
    absences = base_absences + [
        Absence(100, 1, AbsenceType.U, start, start + timedelta(days=13), "Test Urlaub"),
        Absence(101, 3, AbsenceType.AU, start + timedelta(days=7), start + timedelta(days=14), "Test Krank"),
    ]
    
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    print(f"\nPlanning period: {start} to {end} (4 weeks)")
    print(f"Added test absences:")
    print(f"  - Employee 1: 2-week vacation")
    print(f"  - Employee 3: 1-week sick leave")
    
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
    
    # Check that employees with absences work less (and that's OK)
    emp_hours = {}
    for assignment in assignments:
        emp_id = assignment.employee_id
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
    
    # Employee 1 and 3 should work less due to absences
    emp1_hours = emp_hours.get(1, 0)
    emp3_hours = emp_hours.get(3, 0)
    
    print(f"\nEmployee 1 (with 2-week absence): {emp1_hours}h (expected < 192h)")
    print(f"Employee 3 (with 1-week absence): {emp3_hours}h (expected < 192h)")
    
    if emp1_hours < 192 and emp3_hours < 192:
        print("\n✅ SUCCESS: Absences properly exempt employees from minimum hours!")
        return True
    else:
        print("\n❌ FAILURE: Absence exemption not working properly")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("COMPREHENSIVE MINIMUM WORKING HOURS TESTS")
    print("=" * 80)
    
    results = []
    
    # Test 1: 48h/week configuration (problem statement example)
    results.append(("48h/week configuration", test_minimum_hours_with_48h_config()))
    
    # Test 2: 40h/week configuration (dynamic verification)
    results.append(("40h/week configuration", test_minimum_hours_with_40h_config()))
    
    # Test 3: Absence exemption
    results.append(("Absence exemption", test_absence_exemption()))
    
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
