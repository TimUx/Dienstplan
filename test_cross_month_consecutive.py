"""
Test to verify that consecutive shifts constraint checks across month boundaries.

This test validates that the consecutive days constraint properly considers shifts
from the previous month when checking for violations at the beginning of the
current planning period.

Example scenario:
- Employee works 4 shifts at end of January (Jan 28-31)
- Employee works 4 shifts at start of February (Feb 1-4)
- Total: 8 consecutive days → VIOLATION should be detected
"""

from datetime import date, timedelta
from ortools.sat.python import cp_model
from entities import Employee, Team, ShiftType
from constraints import add_consecutive_shifts_constraints


def test_cross_month_consecutive_violation():
    """
    Test that consecutive shifts spanning month boundaries are detected.
    
    Scenario:
    - Max consecutive days for S shift: 6
    - Employee worked S shift on March 26-31 (4 weekdays: Thu-Fri, Mon-Tue)
    - Planning for April: Employee assigned S shift on April 1-4 (4 weekdays: Wed-Thu-Fri-Sat actually, only Wed-Fri = 3 weekdays)
    - Total: 4 + 3 = 7 consecutive weekdays → VIOLATION (exceeds limit of 6)
    """
    print("\n" + "="*80)
    print("TEST: Cross-Month Consecutive Shifts Violation Detection")
    print("="*80)
    
    # Setup
    model = cp_model.CpModel()
    
    # Employee and team
    employee = Employee(id=1, vorname="Test", name="Employee", team_id=1, personalnummer="PN001")
    team = Team(id=1, name="Test Team")
    employees = [employee]
    teams = [team]
    
    # Shift types
    shift_s = ShiftType(id=3, code="S", name="Spätschicht",
                       start_time="14:00", end_time="22:00", max_consecutive_days=6)
    shift_types = [shift_s]
    shift_codes = ["S"]
    
    # Planning period: April 1-14 (2 weeks)
    start_date = date(2026, 4, 1)  # Wednesday
    dates = [start_date + timedelta(days=i) for i in range(14)]
    
    # Weeks (Sunday to Saturday)
    # April 1 is Wednesday, so we need to extend back to previous Sunday (March 30)
    # But for simplicity, let's just work with the dates we have
    weeks = []
    current_week = []
    for d in dates:
        current_week.append(d)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    if current_week:
        weeks.append(current_week)
    
    # Previous shifts: Employee worked S shift on March 26-31
    # March 26 (Thu), 27 (Fri), 30 (Mon), 31 (Tue) = 4 weekdays
    previous_employee_shifts = {
        (employee.id, date(2026, 3, 26)): "S",  # Thursday
        (employee.id, date(2026, 3, 27)): "S",  # Friday
        (employee.id, date(2026, 3, 30)): "S",  # Monday
        (employee.id, date(2026, 3, 31)): "S",  # Tuesday
    }
    
    # Variables
    employee_active = {}
    employee_weekend_shift = {}
    team_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    
    # Team has S shift in both weeks
    team_shift[(team.id, 0, "S")] = model.NewBoolVar("team_1_week_0_S")
    team_shift[(team.id, 1, "S")] = model.NewBoolVar("team_1_week_1_S")
    model.Add(team_shift[(team.id, 0, "S")] == 1)  # Force S shift in week 0
    model.Add(team_shift[(team.id, 1, "S")] == 1)  # Force S shift in week 1
    
    # Employee is active on first 5 weekdays (Wed-Fri of week 1, plus Mon-Tue of week 2)
    # April 1 (Wed), 2 (Thu), 3 (Fri), 6 (Mon), 7 (Tue) = 5 weekdays
    weekday_count = 0
    for i, d in enumerate(dates):
        if d.weekday() < 5 and weekday_count < 5:  # Weekday, and limit to first 5
            var = model.NewBoolVar(f"emp_1_active_{i}")
            model.Add(var == 1)  # Force active
            employee_active[(employee.id, d)] = var
            weekday_count += 1
    
    print("\nSetup:")
    print(f"  Planning period: {dates[0]} to {dates[-1]}")
    print(f"  Previous shifts (March): 26 (Thu), 27 (Fri), 30 (Mon), 31 (Tue) - 4 weekdays of S shift")
    print(f"  Current period (April): 1 (Wed), 2 (Thu), 3 (Fri), 6 (Mon), 7 (Tue) - 5 weekdays of S shift")
    print(f"  S shift max consecutive days: {shift_s.max_consecutive_days}")
    print(f"  Total consecutive weekdays: 4 (March) + 5 (April) = 9 days")
    print(f"  Expected: VIOLATION (9 > 6)")
    
    # Add constraints
    penalties = add_consecutive_shifts_constraints(
        model, employee_active, employee_weekend_shift, team_shift,
        employee_cross_team_shift, employee_cross_team_weekend,
        employees, teams, dates, weeks, shift_codes, shift_types,
        previous_employee_shifts
    )
    
    print(f"\nConstraint generated {len(penalties)} penalty variables")
    
    # Solve to see if violations are detected
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        total_penalty = sum(solver.Value(p) for p in penalties)
        num_violations = sum(1 for p in penalties if solver.Value(p) > 0)
        
        print(f"\nResults:")
        print(f"  Status: {solver.StatusName(status)}")
        print(f"  Total penalty: {total_penalty}")
        print(f"  Number of violations: {num_violations}")
        
        if total_penalty > 0:
            print(f"  ✅ PASS: Violations detected (penalty = {total_penalty})")
            return True
        else:
            print(f"  ❌ FAIL: No violations detected, but should have found cross-month violation")
            return False
    else:
        print(f"  ❌ FAIL: Solver status: {solver.StatusName(status)}")
        return False


def test_cross_month_no_violation():
    """
    Test that non-violations are not falsely detected across months.
    
    Scenario:
    - Max consecutive days for S shift: 6
    - Employee worked S shift on Jan 30, 31 (2 days)
    - Planning for Feb: Employee assigned S shift on Feb 1, 2, 3 (3 days)
    - Total: 5 consecutive days → NO VIOLATION (within limit of 6)
    """
    print("\n" + "="*80)
    print("TEST: Cross-Month No False Positive")
    print("="*80)
    
    # Setup
    model = cp_model.CpModel()
    
    # Employee and team
    employee = Employee(id=1, vorname="Test", name="Employee", team_id=1, personalnummer="PN001")
    team = Team(id=1, name="Test Team")
    employees = [employee]
    teams = [team]
    
    # Shift types
    shift_s = ShiftType(id=3, code="S", name="Spätschicht", 
                       start_time="14:00", end_time="22:00", max_consecutive_days=6)
    shift_types = [shift_s]
    shift_codes = ["S"]
    
    # Planning period: Feb 1-14 (2 weeks)
    start_date = date(2026, 2, 1)  # Sunday
    dates = [start_date + timedelta(days=i) for i in range(14)]
    
    # Weeks (Sunday to Saturday)
    weeks = [dates[:7], dates[7:14]]
    
    # Previous shifts: Employee worked S shift on Jan 30-31 (2 days only)
    previous_employee_shifts = {
        (employee.id, date(2026, 1, 30)): "S",
        (employee.id, date(2026, 1, 31)): "S",
    }
    
    # Variables
    employee_active = {}
    employee_weekend_shift = {}
    team_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    
    # Team has S shift in first week
    team_shift[(team.id, 0, "S")] = model.NewBoolVar("team_1_week_0_S")
    model.Add(team_shift[(team.id, 0, "S")] == 1)  # Force S shift in week 0
    
    # Employee is active on first 3 weekdays (Mon-Wed)
    for i, d in enumerate(dates[:5]):
        if d.weekday() < 3:  # Mon, Tue, Wed only
            var = model.NewBoolVar(f"emp_1_active_{i}")
            model.Add(var == 1)  # Force active
            employee_active[(employee.id, d)] = var
    
    print("\nSetup:")
    print(f"  Planning period: {dates[0]} to {dates[-1]}")
    print(f"  Previous shifts (Jan): 30, 31 (2 days of S shift)")
    print(f"  Current period: Employee assigned S shift on Feb 1, 2, 3 (3 days)")
    print(f"  S shift max consecutive days: {shift_s.max_consecutive_days}")
    print(f"  Total consecutive days: 2 (Jan) + 3 (Feb) = 5 days")
    print(f"  Expected: NO VIOLATION (5 <= 6)")
    
    # Add constraints
    penalties = add_consecutive_shifts_constraints(
        model, employee_active, employee_weekend_shift, team_shift,
        employee_cross_team_shift, employee_cross_team_weekend,
        employees, teams, dates, weeks, shift_codes, shift_types,
        previous_employee_shifts
    )
    
    print(f"\nConstraint generated {len(penalties)} penalty variables")
    
    # Solve to see if violations are detected
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        total_penalty = sum(solver.Value(p) for p in penalties)
        num_violations = sum(1 for p in penalties if solver.Value(p) > 0)
        
        print(f"\nResults:")
        print(f"  Status: {solver.StatusName(status)}")
        print(f"  Total penalty: {total_penalty}")
        print(f"  Number of violations: {num_violations}")
        
        if total_penalty == 0:
            print(f"  ✅ PASS: No false positives")
            return True
        else:
            print(f"  ❌ FAIL: False positive detected (penalty = {total_penalty})")
            return False
    else:
        print(f"  ❌ FAIL: Solver status: {solver.StatusName(status)}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CROSS-MONTH CONSECUTIVE SHIFTS CONSTRAINT TESTS")
    print("="*80)
    
    test1 = test_cross_month_consecutive_violation()
    test2 = test_cross_month_no_violation()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Test 1 (Cross-month violation): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (No false positive): {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        exit(1)
