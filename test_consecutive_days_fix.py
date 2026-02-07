#!/usr/bin/env python3
"""
Test to verify that the max consecutive days constraint fix works correctly.

This test validates that the bug fix in constraints.py properly catches
violations when employees work more than the allowed consecutive days
for a specific shift type.
"""

from datetime import date, timedelta
from ortools.sat.python import cp_model
from entities import ShiftType, Employee, Team
from constraints import add_consecutive_shifts_constraints


def test_consecutive_night_shifts_violation():
    """
    Test the exact scenario from the problem statement:
    Employee works 6 consecutive night shifts, which should violate
    the max_consecutive_days=3 rule for night shifts.
    """
    
    print("Test: 6 consecutive night shifts (should violate max=3)")
    print("=" * 70)
    
    # Create test data
    shift_n = ShiftType(
        id=3, code="N", name="Nachtschicht", start_time="21:45", end_time="05:45",
        color_code="#2196F3", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=3, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=3  # Maximum 3 consecutive night shifts
    )
    
    shift_f = ShiftType(
        id=1, code="F", name="Frühschicht", start_time="05:45", end_time="13:45",
        color_code="#4CAF50", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=4, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=6
    )
    
    team = Team(id=1, name="Team Alpha")
    employee = Employee(
        id=1, vorname="Anna", name="Schmidt", personalnummer="PN002", team_id=1
    )
    
    # Create a 14-day period where employee works 6 consecutive night shifts (days 8-13)
    # Day 1-7: F shifts (week 1)
    # Day 8-14: N shifts (week 2) - 6 consecutive days violates max=3
    start_date = date(2026, 2, 1)
    dates = [start_date + timedelta(days=i) for i in range(14)]
    
    # Create weeks
    week1 = dates[0:7]   # Days 1-7
    week2 = dates[7:14]  # Days 8-14
    weeks = [week1, week2]
    
    # Setup CP model
    model = cp_model.CpModel()
    
    # Create variables
    employee_active = {}
    employee_weekend_shift = {}
    team_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    
    # Week 1: Team has F shift, employee is active on weekdays
    for day in week1:
        if day.weekday() < 5:  # Weekday
            employee_active[(1, day)] = model.NewBoolVar(f"active_1_{day}")
            model.Add(employee_active[(1, day)] == 1)  # Force active
    
    team_shift[(1, 0, "F")] = model.NewBoolVar("team_1_week_0_F")
    model.Add(team_shift[(1, 0, "F")] == 1)  # Team has F shift in week 1
    
    # Week 2: Team has N shift, employee is active on weekdays
    for day in week2:
        if day.weekday() < 5:  # Weekday
            employee_active[(1, day)] = model.NewBoolVar(f"active_1_{day}")
            model.Add(employee_active[(1, day)] == 1)  # Force active
    
    team_shift[(1, 1, "N")] = model.NewBoolVar("team_1_week_1_N")
    model.Add(team_shift[(1, 1, "N")] == 1)  # Team has N shift in week 2
    
    # Call the constraint function
    shift_types = [shift_f, shift_n]
    shift_codes = ["F", "N"]
    employees = [employee]
    teams = [team]
    
    print("\nSetup:")
    print(f"  Dates: {dates[0]} to {dates[-1]}")
    print(f"  Week 1 (days 1-7): Team has F shift")
    print(f"  Week 2 (days 8-14): Team has N shift")
    print(f"  Employee is active on all weekdays")
    print(f"  Night shift max consecutive days: {shift_n.max_consecutive_days}")
    
    penalties = add_consecutive_shifts_constraints(
        model, employee_active, employee_weekend_shift, team_shift,
        employee_cross_team_shift, employee_cross_team_weekend,
        employees, teams, dates, weeks, shift_codes, shift_types
    )
    
    print(f"\nConstraint generated {len(penalties)} penalty variables")
    
    # Solve to see if violations are detected
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        total_penalty = sum(solver.Value(p) for p in penalties)
        print(f"\nResult: Total penalty = {total_penalty}")
        
        # Debug: Print all penalties
        print(f"\nDebug: Examining {len(penalties)} penalty variables:")
        for i, p in enumerate(penalties):
            val = solver.Value(p)
            if val > 0:
                print(f"  Penalty {i}: {p} = {val}")
        
        # Count violations per shift type
        n_violations = 0
        f_violations = 0
        for p in penalties:
            if solver.Value(p) > 0:
                pname = str(p)
                if "_N_" in pname or pname.startswith("N_"):
                    n_violations += 1
                elif "_F_" in pname or pname.startswith("F_"):
                    f_violations += 1
        
        print(f"\n  Night shift (N) violations: {n_violations}")
        print(f"  F shift violations: {f_violations}")
        
        if n_violations > 0 or total_penalty >= 400:  # At least one violation
            print("\n✅ SUCCESS: Violations properly detected!")
            print(f"   The constraint correctly identified that 6 consecutive N shifts")
            print(f"   violates the max_consecutive_days=3 rule.")
        else:
            print("\n❌ FAIL: No violations detected!")
            print(f"   The constraint failed to catch 6 consecutive N shifts")
            print(f"   despite max_consecutive_days=3 limit.")
            return False
    else:
        print(f"\n⚠️  Solver status: {solver.StatusName(status)}")
        return False
    
    return True


def test_mixed_shift_scenario():
    """
    Test a scenario where employee switches between shift types.
    This should NOT violate consecutive days constraint.
    """
    
    print("\n\nTest: Switching shift types (should NOT violate)")
    print("=" * 70)
    
    # Create test data
    shift_n = ShiftType(
        id=3, code="N", name="Nachtschicht", start_time="21:45", end_time="05:45",
        color_code="#2196F3", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=3, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=3
    )
    
    shift_f = ShiftType(
        id=1, code="F", name="Frühschicht", start_time="05:45", end_time="13:45",
        color_code="#4CAF50", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=4, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=6
    )
    
    team = Team(id=1, name="Team Alpha")
    employee = Employee(
        id=1, vorname="Test", name="Employee", personalnummer="PN001", team_id=1
    )
    
    # Create a 7-day period: 3 N shifts, then 4 F shifts
    start_date = date(2026, 2, 1)
    dates = [start_date + timedelta(days=i) for i in range(7)]
    weeks = [dates]
    
    # Setup CP model
    model = cp_model.CpModel()
    
    employee_active = {}
    employee_weekend_shift = {}
    team_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    td_vars = {}
    
    # Use cross-team shifts to simulate: N N N F F F F
    for i, day in enumerate(dates):
        if i < 3:  # First 3 days: N shift
            var = model.NewBoolVar(f"cross_N_{i}")
            model.Add(var == 1)
            employee_cross_team_shift[(1, day, "N")] = var
        else:  # Next 4 days: F shift
            var = model.NewBoolVar(f"cross_F_{i}")
            model.Add(var == 1)
            employee_cross_team_shift[(1, day, "F")] = var
    
    print("\nSetup:")
    print(f"  Days 1-3: N shifts")
    print(f"  Days 4-7: F shifts")
    print(f"  Night shift max consecutive days: {shift_n.max_consecutive_days}")
    print(f"  F shift max consecutive days: {shift_f.max_consecutive_days}")
    
    shift_types = [shift_f, shift_n]
    shift_codes = ["F", "N"]
    employees = [employee]
    teams = [team]
    
    penalties = add_consecutive_shifts_constraints(
        model, employee_active, employee_weekend_shift, team_shift,
        employee_cross_team_shift, employee_cross_team_weekend,
        employees, teams, dates, weeks, shift_codes, shift_types
    )
    
    print(f"\nConstraint generated {len(penalties)} penalty variables")
    
    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        total_penalty = sum(solver.Value(p) for p in penalties)
        print(f"\nResult: Total penalty = {total_penalty}")
        
        if total_penalty == 0:
            print("\n✅ SUCCESS: No violations detected (as expected)")
            print(f"   Switching from N to F after 3 days is allowed.")
        else:
            print("\n❌ FAIL: Unexpected violations detected!")
            return False
    else:
        print(f"\n⚠️  Solver status: {solver.StatusName(status)}")
        return False
    
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("TESTING MAX CONSECUTIVE DAYS CONSTRAINT FIX")
    print("=" * 70)
    print()
    
    success = True
    
    # Test 1: Violation scenario
    if not test_consecutive_night_shifts_violation():
        success = False
    
    # Test 2: Non-violation scenario
    if not test_mixed_shift_scenario():
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
