"""
Test to verify that consecutive shifts constraint is NOT bypassed when 
planning subsequent months that re-plan boundary weeks.

Scenario:
1. Plan January: Employee gets shifts Jan 20-26 (7 days, boundary week)
2. Plan February: Planning extends back to Jan 26, re-plans that boundary week
   - previous_employee_shifts only includes shifts before Jan 26
   - But employee worked Jan 20-25 (6 days), then boundary week Jan 26-31 is re-planned
   - If Feb 1-5 are also planned with shifts, total could be > 6 consecutive days
   
This test demonstrates the bug where boundary week re-planning bypasses 
consecutive days checking across the previous month's non-boundary days.
"""

from datetime import date, timedelta
from ortools.sat.python import cp_model
from entities import Employee, Team, ShiftType
from constraints import add_consecutive_shifts_constraints


def test_boundary_week_replanning_bypass():
    """
    Test that demonstrates the consecutive days limit bypass through boundary week re-planning.
    
    Scenario:
    - Max consecutive days for S shift: 6
    - Month 1: Employee worked S shift Jan 20-25 (6 days, ending before boundary week)
    - Month 1 boundary: Jan 26-31 (boundary week, planned in Month 1)
    - Month 2: Planning extends to Jan 26, doesn't lock Jan 26-31 (boundary week)
    - previous_employee_shifts only has Jan 19 and earlier (extended_start is Jan 26)
    - System plans Jan 26 - Feb 10
    - If system schedules S shifts on Jan 26-Feb 2, that's 8 consecutive days with Jan 20-25
    - BUT the constraint only sees Jan 19 and earlier in previous_employee_shifts!
    
    Expected: Should detect violation (6 + 8 = 14 consecutive days)
    Actual: Might miss it because Jan 20-25 are not in previous_employee_shifts (they're after extended_start - max_consecutive_days)
    """
    print("\n" + "="*80)
    print("TEST: Boundary Week Re-planning Consecutive Days Bypass")
    print("="*80)
    
    # Setup
    model = cp_model.CpModel()
    
    # Employee and team
    employee = Employee(id=1, vorname="Lisa", name="Meyer", team_id=1, personalnummer="PN004")
    team = Team(id=1, name="Team Alpha")
    employees = [employee]
    teams = [team]
    
    # Shift types
    shift_s = ShiftType(id=3, code="S", name="Spätschicht",
                       start_time="14:00", end_time="22:00", max_consecutive_days=6)
    shift_types = [shift_s]
    shift_codes = ["S"]
    
    # Simulating planning for "Month 2" which extends back to include boundary week
    # Planning period: Jan 26 - Feb 10 (16 days, 2+ weeks)
    # extended_start = Jan 26 (boundary week from previous month)
    # lookback_start = Jan 26 - 7 = Jan 19
    # lookback_end = Jan 25
    extended_start = date(2026, 1, 26)  # Sunday, start of boundary week
    dates = [extended_start + timedelta(days=i) for i in range(16)]
    
    # Weeks (Sunday to Saturday)
    weeks = []
    current_week = []
    for d in dates:
        current_week.append(d)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    if current_week:
        weeks.append(current_week)
    
    # Previous shifts: Employee worked S shift on Jan 19-25 (7 days)
    # These are what would be in previous_employee_shifts based on lookback
    # lookback_start = Jan 19, lookback_end = Jan 25
    # But wait - if max_consecutive_days = 6, lookback would be Jan 19-25
    # Actually, the issue is subtler...
    
    # Let's simulate what REALLY happens:
    # Month 1 planning: Jan 1-31, extended to Jan 1 - Feb 1 (to complete last week)
    # Employee gets S shifts Jan 20-31 (12 consecutive days) - VIOLATION! But already saved
    # Month 2 planning: Feb 1-28, extended to Jan 26 - Feb 28 (to complete first week)
    # lookback_start = Jan 26 - 6 = Jan 20
    # lookback_end = Jan 25  
    # So previous_employee_shifts WOULD include Jan 20-25
    # But Jan 26-31 are in the planning period and NOT LOCKED (boundary week)
    # And Feb 1-10 are also in planning period
    
    # Wait, I need to recalculate. If extended_start = Jan 26:
    # lookback = extended_start - max_consecutive_limit
    # If max_consecutive_limit = 6 (assuming same as max_consecutive_days):
    # lookback_start = Jan 20, lookback_end = Jan 25
    
    previous_employee_shifts = {
        (employee.id, date(2026, 1, 20)): "S",  # Monday
        (employee.id, date(2026, 1, 21)): "S",  # Tuesday
        (employee.id, date(2026, 1, 22)): "S",  # Wednesday
        (employee.id, date(2026, 1, 23)): "S",  # Thursday
        (employee.id, date(2026, 1, 24)): "S",  # Friday
        (employee.id, date(2026, 1, 25)): "S",  # Saturday
    }
    
    print("\nScenario Simulation:")
    print(f"  Month 1 was planned: Jan 1-31")
    print(f"  Employee worked: Jan 20-25 (6 consecutive days, saved in DB)")
    print(f"  Month 2 planning: Feb 1-28")
    print(f"  Extended planning: Jan 26 - Feb 28 (includes boundary week)")
    print(f"  previous_employee_shifts: Jan 20-25 (6 days)")
    print(f"  Planning will assign: Jan 26 - Feb 10")
    print(f"  If system assigns S shifts on Jan 26 - Feb 2 (8 days):")
    print(f"    Total = 6 (previous) + 8 (current) = 14 consecutive days")
    print(f"  S shift max consecutive days: {shift_s.max_consecutive_days}")
    print(f"  Expected: VIOLATION (14 > 6)")
    
    # Variables
    employee_active = {}
    employee_weekend_shift = {}
    team_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    
    # Team has S shift in both weeks
    for week_idx in range(len(weeks)):
        team_shift[(team.id, week_idx, "S")] = model.NewBoolVar(f"team_1_week_{week_idx}_S")
        model.Add(team_shift[(team.id, week_idx, "S")] == 1)  # Force S shift
    
    # Employee is active on Jan 26 - Feb 2 (8 consecutive days)
    for i, d in enumerate(dates[:8]):  # First 8 days
        if d.weekday() < 5:  # Weekday
            var = model.NewBoolVar(f"emp_1_active_{i}")
            model.Add(var == 1)  # Force active
            employee_active[(employee.id, d)] = var
        else:  # Weekend
            var = model.NewBoolVar(f"emp_1_weekend_{i}")
            model.Add(var == 1)  # Force active
            employee_weekend_shift[(employee.id, d)] = var
    
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
            print(f"  The constraint correctly detected consecutive days across planning periods")
            return True
        else:
            print(f"  ❌ FAIL: No violations detected!")
            print(f"  BUG: The constraint should have detected 6 + 8 = 14 consecutive days > 6 limit")
            print(f"  This demonstrates the boundary week re-planning bypass issue")
            return False
    else:
        print(f"  ❌ FAIL: Solver status: {solver.StatusName(status)}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("BOUNDARY WEEK RE-PLANNING CONSECUTIVE DAYS BYPASS TEST")
    print("="*80)
    
    result = test_boundary_week_replanning_bypass()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    if result:
        print("✅ TEST PASSED - Constraint works correctly across planning periods")
    else:
        print("❌ TEST FAILED - Boundary week re-planning bypasses consecutive days checking")
        print("\nThis confirms the bug described in the issue:")
        print("When planning month N+1, the system re-plans boundary weeks from month N,")
        print("but the consecutive days constraint only checks against shifts before the")
        print("extended planning start date, missing the non-boundary shifts from month N.")
        exit(1)
