from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Set, Tuple
from entities import Employee, Absence, ShiftType, Team, get_shift_type_by_id
from .constants import (
    CROSS_MONTH_BOUNDARY_PENALTY,
    DEFAULT_MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS_WEEKS,
    DEFAULT_MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS,
    DEFAULT_MINIMUM_REST_HOURS,
    DEFAULT_ROTATION_PATTERN,
    DEFAULT_WEEKLY_HOURS,
)


def add_working_hours_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType],
    absences: List[Absence] = None,
    violation_tracker=None,
    target_start_date: date = None,
    target_end_date: date = None,
) -> List[cp_model.IntVar]:
    """
    HARD + SOFT CONSTRAINT: Working hours target based on proportional calculation INCLUDING cross-team.
    
    This constraint ensures that employees:
    1. HARD: Minimum 192h/month (24 shifts × 8h) - Required minimum work hours
       - Ensures employees work at least 24 shifts per month
       - Only applies to employees without full-month absences
    2. SOFT: Target proportional hours (48h/7 × days) - e.g., 212h for 31-day month
       - Solver minimizes shortage from target
       - Violations tracked for admin review
    3. Do not exceed maximum weekly hours (WeeklyWorkingHours from shift configuration) - HARD
    4. Absences (U/AU/L) are exceptions - employees are not required to make up hours lost to absences
    5. If an employee works less in one week (without absence), they should compensate in other weeks (SOFT)
    6. UPDATED: Hours from cross-team assignments count toward employee's total hours
    
    FIX (2026-02-04): Changed from week-based to day-based absence handling.
    Previously, if an employee had an absence on ANY day of a week, the ENTIRE week was skipped
    when calculating hours. This caused hours worked on non-absent days to not be counted.
    Now only individual absent DAYS are skipped, allowing proper hour calculation for partial-week absences.
    
    FIX (2026-04-18): Added target_start_date / target_end_date parameters.
    The planning model extends dates to complete calendar weeks (e.g. March extends to April 4th).
    Without filtering, the hours target is computed for 35 days instead of the actual 31 days of
    March, making the target artificially high and causing the solver to understate how well
    employees are meeting their monthly obligation.  Both the target and the actual hours now
    only count days within [target_start_date, target_end_date].
    
    Example: Employee has AU on March 1 (Sunday) but worked Feb 23-28. Previously week 4 (Feb 23-Mar 1)
    was completely skipped. Now only March 1 is skipped, and Feb 23-28 hours are properly counted.
    
    Args:
        target_start_date: First day of the planning MONTH (not the extended week boundary).
                           When None, all dates in the extended period are used (backward-compat).
        target_end_date:   Last day of the planning MONTH.  Same behaviour as target_start_date.
    
    Returns:
        List of IntVar representing shortage from target hours for soft optimization
    
    The limits are now DYNAMIC per employee based on their team's assigned shift(s),
    replacing the previous fixed limits of 192 hours/month and 48 hours/week.
    
    Note: All main shifts (F, S, N) are 8 hours by default.
    Weekend hours are based on team's shift type (same as weekday).
    Cross-team hours are based on the actual shift worked.
    """
    absences = absences or []
    
    # Initialize list for soft objective variables (minimize shortage from target hours)
    soft_objectives = []
    
    # Create shift hours lookup
    shift_hours = {}
    shift_weekly_hours = {}
    for st in shift_types:
        shift_hours[st.code] = st.hours
        shift_weekly_hours[st.code] = st.weekly_working_hours
    
    # Restrict hours accounting to the original planning month.
    # The planning model may extend dates to complete calendar weeks (e.g. a March
    # planning run covers 2026-03-01 to 2026-04-04 = 35 days).  Computing the target
    # over all 35 days inflates the monthly obligation by ~13 %.  Instead we only
    # count days inside [target_start_date, target_end_date] (e.g. March 1–31).
    if target_start_date is not None and target_end_date is not None:
        target_date_set = frozenset(d for d in dates if target_start_date <= d <= target_end_date)
    else:
        target_date_set = frozenset(dates)
    # The system only enforces:
    # - SOFT target: proportional hours over the entire planning period
    # - NO hard weekly limits
    for emp in employees:
        if not emp.team_id:
            continue  # Only check team members
        
        for week_idx, week_dates in enumerate(weeks):
            # Calculate hours for this week
            hours_terms = []
            
            # For each shift type, calculate hours if team has that shift
            for shift_code in shift_codes:
                if (emp.team_id, week_idx, shift_code) not in team_shift:
                    continue
                if shift_code not in shift_hours:
                    continue
                
                # Count all active days (weekday + weekend) for this employee when team has this shift
                active_days = []
                
                # WEEKDAY days
                for d in week_dates:
                    if d.weekday() < 5 and (emp.id, d) in employee_active:
                        active_days.append(employee_active[(emp.id, d)])
                
                # WEEKEND days (same shift type as team)
                for d in week_dates:
                    if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                        active_days.append(employee_weekend_shift[(emp.id, d)])
                
                if not active_days:
                    continue
                
                # Count active days this week
                days_active = model.NewIntVar(0, len(week_dates), 
                                              f"emp{emp.id}_week{week_idx}_days")
                model.Add(days_active == sum(active_days))
                
                # Conditional active days: non-zero only when team has this shift
                # Use OnlyEnforceIf (linear) instead of AddMultiplicationEquality (non-linear)
                # This is significantly faster for CP-SAT to solve.
                team_shift_var = team_shift[(emp.team_id, week_idx, shift_code)]
                conditional_days = model.NewIntVar(0, len(week_dates), 
                                                   f"emp{emp.id}_week{week_idx}_shift{shift_code}_days")
                model.Add(conditional_days == days_active).OnlyEnforceIf(team_shift_var)
                model.Add(conditional_days == 0).OnlyEnforceIf(team_shift_var.Not())
                
                # Multiply by hours (scaled by 10)
                scaled_hours = int(shift_hours[shift_code] * 10)
                hours_terms.append(conditional_days * scaled_hours)
            
            # ADD: Count cross-team hours this week
            for shift_code in shift_codes:
                if shift_code not in shift_hours:
                    continue
                
                cross_team_days = []
                for d in week_dates:
                    if d.weekday() < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        cross_team_days.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    elif d.weekday() >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        cross_team_days.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                if cross_team_days:
                    # Count cross-team days for this shift
                    cross_days_count = model.NewIntVar(0, len(week_dates), 
                                                       f"emp{emp.id}_week{week_idx}_crossteam{shift_code}_days")
                    model.Add(cross_days_count == sum(cross_team_days))
                    
                    # Multiply by hours (scaled by 10)
                    scaled_hours = int(shift_hours[shift_code] * 10)
                    hours_terms.append(cross_days_count * scaled_hours)
            
            # NOTE: No hard weekly maximum hours constraint
            # Employees can work varying hours per week (e.g., 40h one week, 56h another)
            # as long as the overall period targets are met
    
    # MINIMUM working hours constraint across the planning period
    # 
    # Business requirement (per @TimUx - updated 2026-01-25 in PR #122):
    # - SOFT CONSTRAINT: Target minimum proportional to days: (weekly_working_hours/7) × days_in_period
    #   → Example: January 31 days, 48h/week → 48/7 × 31 = 212.57h ≈ 213h target
    #   → Example: February 28 days, 48h/week → 48/7 × 28 = 192h target
    #   → Example: Custom shift 40h/week, 30 days → 40/7 × 30 = 171.43h ≈ 171h target
    # - Hours can vary per week (e.g., 56h one week, 40h another week)
    # - Only absences (sick, vacation, training) exempt employees from these requirements
    # - Minimum staffing (e.g., F=4, S=3, N=3) is a FLOOR - more employees SHOULD work to meet hours
    # - Rules should be followed but can be violated if necessary for planning feasibility
    # - Violations are tracked and minimized via high penalty weight
    # 
    # Implementation:
    # - Soft constraint with HIGH penalty: minimize shortage from target hours
    # - Target = (weekly_working_hours / 7) × days_without_absence
    # - Penalty weight: 100x (very high priority, but not absolute)
    # - Shift hours come from shift settings (ShiftType.hours)
    # - Weekly hours come from shift settings (ShiftType.weekly_working_hours)
    for emp in employees:
        if not emp.team_id:
            continue  # Only check team members
        
        # Calculate total hours worked across all weeks
        total_hours_terms = []
        
        # PERFORMANCE OPTIMIZATION: Pre-compute absent dates for this employee once
        # This avoids O(dates × absences) complexity in nested loops
        absent_dates = set()
        for d in dates:
            if any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences):
                absent_dates.add(d)
        
        # Calculate total days without absences for this employee
        # Use only target-period days so that extended-week days (e.g. April 1-4 when
        # planning March) do not inflate the monthly hours obligation.
        days_without_absence = sum(1 for d in target_date_set if d not in absent_dates)
        
        # Track weekly target hours (use shift settings from last week with shifts)
        weekly_target_hours = DEFAULT_WEEKLY_HOURS  # Default if no shifts found
        
        for week_idx, week_dates in enumerate(weeks):
            # FIX: Don't skip entire weeks with absences - count hours on non-absent days
            # Calculate hours worked this week based on team's shift assignment
            # Note: Only ONE shift is active per team per week due to team_shift constraints
            for shift_code in shift_codes:
                if (emp.team_id, week_idx, shift_code) not in team_shift:
                    continue
                if shift_code not in shift_hours:
                    continue
                
                # Update weekly target from shift settings
                if shift_code in shift_weekly_hours:
                    weekly_target_hours = shift_weekly_hours[shift_code]
                
                # Count all active days (weekday + weekend) for this employee when team has this shift
                # Only count days inside the target period and WITHOUT absences.
                active_days = []
                
                # WEEKDAY days
                for d in week_dates:
                    # Skip days outside the target month or with absences
                    if d not in target_date_set:
                        continue
                    if d in absent_dates:
                        continue
                    
                    if d.weekday() < 5 and (emp.id, d) in employee_active:
                        active_days.append(employee_active[(emp.id, d)])
                
                # WEEKEND days (same shift type as team)
                for d in week_dates:
                    # Skip days outside the target month or with absences
                    if d not in target_date_set:
                        continue
                    if d in absent_dates:
                        continue
                    
                    if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                        active_days.append(employee_weekend_shift[(emp.id, d)])
                
                if not active_days:
                    continue
                
                # Count active days this week
                days_active = model.NewIntVar(0, len(week_dates), 
                                              f"emp{emp.id}_week{week_idx}_days_min")
                model.Add(days_active == sum(active_days))
                
                # Conditional active days: non-zero only when team has this shift
                # Use OnlyEnforceIf (linear) instead of AddMultiplicationEquality (non-linear)
                # This is significantly faster for CP-SAT to solve.
                team_shift_var = team_shift[(emp.team_id, week_idx, shift_code)]
                conditional_days = model.NewIntVar(0, len(week_dates), 
                                                   f"emp{emp.id}_week{week_idx}_shift{shift_code}_days_min")
                model.Add(conditional_days == days_active).OnlyEnforceIf(team_shift_var)
                model.Add(conditional_days == 0).OnlyEnforceIf(team_shift_var.Not())
                
                # Multiply by shift hours (from shift settings, scaled by 10)
                scaled_hours = int(shift_hours[shift_code] * 10)
                total_hours_terms.append(conditional_days * scaled_hours)
            
            # ADD: Count cross-team hours this week for minimum hours calculation
            # Only count days inside the target period and WITHOUT absences.
            for shift_code in shift_codes:
                if shift_code not in shift_hours:
                    continue
                
                cross_team_days = []
                for d in week_dates:
                    # Skip days outside the target month or with absences
                    if d not in target_date_set:
                        continue
                    if d in absent_dates:
                        continue
                    
                    if d.weekday() < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        cross_team_days.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    elif d.weekday() >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        cross_team_days.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                if cross_team_days:
                    # Count cross-team days for this shift
                    cross_days_count = model.NewIntVar(0, len(week_dates), 
                                                       f"emp{emp.id}_week{week_idx}_crossteam{shift_code}_days_min")
                    model.Add(cross_days_count == sum(cross_team_days))
                    
                    # Multiply by hours (scaled by 10)
                    scaled_hours = int(shift_hours[shift_code] * 10)
                    total_hours_terms.append(cross_days_count * scaled_hours)
        
        # Apply minimum hours constraints if employee has days without absences
        # FIX: Use days_without_absence (calculated above) instead of weeks_without_absences
        if total_hours_terms and days_without_absence > 0:
            # SOFT CONSTRAINT: Target minimum hours based on proportional calculation
            # Target = (weekly_working_hours / 7) × days_without_absence
            # This is dynamic and adapts to different month lengths and weekly hours
            # 
            # Examples:
            # - January (31 days), 48h/week: 48/7 × 31 = 212.57h ≈ 213h target (scaled: 2130)
            # - February (28 days), 48h/week: 48/7 × 28 = 192h target (scaled: 1920)
            # - March (31 days), 40h/week: 40/7 × 31 = 177.14h ≈ 177h target (scaled: 1770)
            # 
            # High penalty weight (100x) ensures this is strongly enforced, but allows
            # violations when necessary for planning feasibility (per PR #122 requirements)
            
            daily_target_hours = weekly_target_hours / 7.0
            target_total_hours_scaled = int(daily_target_hours * days_without_absence * 10)
            
            # Create variable for shortage from target (0 if at target, positive if below)
            shortage_from_target = model.NewIntVar(0, target_total_hours_scaled, 
                                                    f"emp{emp.id}_hours_shortage")
            
            # shortage = max(0, target - actual)
            # We model this as: shortage >= target - actual AND shortage >= 0
            model.Add(shortage_from_target >= target_total_hours_scaled - sum(total_hours_terms))
            model.Add(shortage_from_target >= 0)
            
            # Add to soft objectives with HIGH penalty weight (100x)
            # This makes it nearly as important as hard constraints, but still flexible
            soft_objectives.append(shortage_from_target * 100)
    
    return soft_objectives


def add_no_gap_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    absences: List[Absence],
    target_start_date: date = None,
    target_end_date: date = None,
) -> List[cp_model.IntVar]:
    """
    SOFT CONSTRAINT: Penalise employees for having zero work days in any week where they
    are present (not fully absent).

    Business requirement: In high-absence situations, present employees must fill their
    monthly target hours.  Leaving present employees idle for entire weeks is therefore
    more costly than minor comfort-constraint violations such as shift-type grouping.

    Weight: 250,000 per idle week.  Calibration:
    - The shift-grouping "isolation" penalty ranges from 100,000 (far-range A-B-A pattern
      over 10+ days) up to 500,000 (ultra-close A-B-A within 7 days).  The most common
      violation in practice is the far-range case at ~100,000–200,000.  By using 250,000
      the no-gap penalty reliably exceeds the common grouping range, ensuring the solver
      prefers to fill a gap even when working triggers a grouping penalty.
    - The minimum-staffing fallback penalty (200,000 × violation count) and the monthly
      hours-shortage penalty (~4,800,000 per week of missing work after scaling) are both
      larger, so those harder obligations still dominate.

    Only days inside [target_start_date, target_end_date] are considered so that extended
    week-boundary days (e.g. Apr 1–4 in a March run) do not generate spurious penalties.

    Returns:
        List of IntVar penalty values to be minimised in the objective.
    """
    NO_WORK_WEEK_PENALTY = 250_000
    gap_penalties = []

    # Restrict to the original planning month (not extended week-boundary days).
    if target_start_date is not None and target_end_date is not None:
        target_date_set = frozenset(d for d in dates if target_start_date <= d <= target_end_date)
    else:
        target_date_set = frozenset(dates)

    # Build employee→team lookup once
    emp_to_team: Dict[int, Team] = {}
    for emp in employees:
        if emp.team_id:
            for t in teams:
                if t.id == emp.team_id:
                    emp_to_team[emp.id] = t
                    break

    for emp in employees:
        if not emp.team_id:
            continue
        team = emp_to_team.get(emp.id)
        if not team:
            continue

        # Pre-compute absent dates once for this employee
        absent_dates = frozenset(
            d for d in dates
            if any(a.employee_id == emp.id and a.overlaps_date(d) for a in absences)
        )

        for week_idx, week_dates in enumerate(weeks):
            # Collect work-indicator variables for non-absent target-period days this week
            work_vars = []
            has_workable_day = False

            for d in week_dates:
                if d not in target_date_set:
                    continue
                if d in absent_dates:
                    continue
                has_workable_day = True
                weekday = d.weekday()

                # Team-shift weekday: employee_active is 1 iff the employee works
                # their team's shift on this day (already enforced by team-linkage constraints)
                if weekday < 5 and (emp.id, d) in employee_active:
                    work_vars.append(employee_active[(emp.id, d)])

                # Team-shift weekend
                if weekday >= 5 and (emp.id, d) in employee_weekend_shift:
                    work_vars.append(employee_weekend_shift[(emp.id, d)])

                # Cross-team assignments (weekday and weekend)
                for sc in shift_codes:
                    if weekday < 5 and (emp.id, d, sc) in employee_cross_team_shift:
                        work_vars.append(employee_cross_team_shift[(emp.id, d, sc)])
                    if weekday >= 5 and (emp.id, d, sc) in employee_cross_team_weekend:
                        work_vars.append(employee_cross_team_weekend[(emp.id, d, sc)])

            if not has_workable_day or not work_vars:
                # Entire week is absent or has no work variables → skip
                continue

            # works_this_week = 1  ↔  at least one work variable is 1
            works_this_week = model.NewBoolVar(f"nogap_works_{emp.id}_w{week_idx}")
            model.Add(sum(work_vars) >= 1).OnlyEnforceIf(works_this_week)
            model.Add(sum(work_vars) == 0).OnlyEnforceIf(works_this_week.Not())

            # Add penalty when employee works zero days this week
            # penalty = 0 if works_this_week else NO_WORK_WEEK_PENALTY
            penalty = model.NewIntVar(0, NO_WORK_WEEK_PENALTY,
                                      f"nogap_pen_{emp.id}_w{week_idx}")
            model.Add(penalty >= NO_WORK_WEEK_PENALTY).OnlyEnforceIf(works_this_week.Not())
            gap_penalties.append(penalty)

    return gap_penalties


def add_weekly_available_employee_constraint(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    weeks: List[List[date]]
):
    """
    HARD CONSTRAINT: Weekly available employee for dynamic coverage.
    
    Requirements:
    - Each week, at least 1 employee from shift-teams must not be assigned to any shift
    - This employee can be dynamically deployed as a substitute in case of absences
    - Must be from regular shift-teams (not special roles like TD-only employees)
    - Must be a team member (not employees without teams)
    
    Implementation:
    - For each week, count total working days for each eligible employee
    - Ensure at least 1 eligible employee has 0 working days that week
    """
    # Get eligible employees: regular shift-team members (not special roles)
    eligible_employees = []
    for emp in employees:
        # Must have a team
        if not emp.team_id:
            continue
        # This is a regular shift-team member
        eligible_employees.append(emp)
    
    if not eligible_employees:
        return  # No eligible employees
    
    # For each week, ensure at least 1 eligible employee is completely free
    for week_idx, week_dates in enumerate(weeks):
        # For each eligible employee, create a variable indicating if they're free this week
        employee_free_vars = []
        
        for emp in eligible_employees:
            # Count working days for this employee in this week
            working_days = []
            
            for d in week_dates:
                if d.weekday() < 5:  # Weekday
                    if (emp.id, d) in employee_active:
                        working_days.append(employee_active[(emp.id, d)])
                else:  # Weekend
                    if (emp.id, d) in employee_weekend_shift:
                        working_days.append(employee_weekend_shift[(emp.id, d)])
            
            if working_days:
                # Create variable: is this employee completely free this week?
                is_free = model.NewBoolVar(f"emp{emp.id}_free_week{week_idx}")
                
                # Employee is free if sum of working days == 0
                # Equivalently: is_free == 1 iff sum(working_days) == 0
                # We can express this as: sum(working_days) <= (1 - is_free) * len(working_days)
                # When is_free=1: sum <= 0 (must be 0)
                # When is_free=0: sum <= len (can be anything)
                model.Add(sum(working_days) == 0).OnlyEnforceIf(is_free)
                model.Add(sum(working_days) >= 1).OnlyEnforceIf(is_free.Not())
                
                employee_free_vars.append(is_free)
        
        if employee_free_vars:
            # At least 1 employee must be completely free this week
            model.Add(sum(employee_free_vars) >= 1)


def add_weekly_block_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    absences: List[Absence]
):
    """
    DISABLED: Mon-Fri block scheduling for cross-team assignments is NOT enforced.
    
    Per @TimUx feedback: Block scheduling should be preferred but NOT mandatory.
    The predefined blocks (Mon-Fri, Mon-Sun, Sat-Sun) should be followed when possible,
    but smaller blocks or individual days can be used if needed to meet minimum hours.
    
    This hard constraint was causing infeasibility by being too restrictive.
    Block scheduling is now handled as SOFT objectives in add_team_member_block_constraints().
    
    Args:
        model: CP-SAT model (unused)
        employee_active: Regular team shift variables (unused)
        employee_cross_team_shift: Cross-team shift variables (unused)
        employees: List of employees (unused)
        dates: All dates in planning period (unused)
        weeks: List of weeks (unused)
        shift_codes: All shift codes (unused)
        absences: Employee absences (unused)
    """
    # INTENTIONALLY DISABLED: Block constraints were too restrictive
    # Cross-team assignments can now be any length (1-7 days) as needed
    # Block preferences are encouraged via soft objectives instead
    pass


def add_team_member_block_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    absences: List[Absence]
) -> List[cp_model.IntVar]:
    """
    SOFT OBJECTIVES: Encourage block scheduling (Mon-Fri, Mon-Sun, Sat-Sun).
    
    Block scheduling preferences (flexible, NOT mandatory):
    1. Prefer Mon-Fri blocks (5 days) when working weekdays
    2. Prefer Mon-Sun blocks (7 days) for full week
    3. Prefer Sat-Sun blocks (2 days) for weekends
    
    The predefined blocks should be followed when possible but are NOT mandatory.
    Smaller blocks can be used if needed. The system will try to use blocks but
    may use individual days if necessary to meet minimum hours requirements.
    
    Args:
        model: CP-SAT model
        employee_active: Regular team shift variables for weekdays (emp_id, date)
        employee_weekend_shift: Weekend shift variables (emp_id, date)
        team_shift: Team shift assignments (team_id, week_idx, shift_code)
        employees: List of employees
        teams: List of teams
        dates: All dates in planning period
        weeks: List of weeks (each week is a list of dates)
        shift_codes: All shift codes
        absences: Employee absences
    
    Returns:
        List of objective variables for block scheduling preferences
    """
    
    objective_vars = []
    
    for emp in employees:
        if not emp.team_id:
            continue
        
        # Find employee's team
        team = None
        for t in teams:
            if t.id == emp.team_id:
                team = t
                break
        
        if not team:
            continue
        
        for week_idx, week_dates in enumerate(weeks):
            # Get weekdays and weekend days in this week
            weekdays = [d for d in week_dates if d.weekday() < 5]
            weekend_days = [d for d in week_dates if d.weekday() >= 5]
            
            # Collect all work variables for the week (for checking isolated days)
            all_week_vars = []
            all_week_dates = []
            
            for d in week_dates:
                is_absent = any(
                    abs.employee_id == emp.id and abs.overlaps_date(d)
                    for abs in absences
                )
                
                if not is_absent:
                    if d.weekday() < 5 and (emp.id, d) in employee_active:
                        all_week_vars.append(employee_active[(emp.id, d)])
                        all_week_dates.append(d)
                    elif d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                        all_week_vars.append(employee_weekend_shift[(emp.id, d)])
                        all_week_dates.append(d)
            
            # SOFT OBJECTIVES: Encourage block scheduling
            
            # Objective 1: Encourage Mon-Fri blocks (all 5 weekdays)
            if len(weekdays) >= 5:
                weekday_vars = []
                for d in weekdays:
                    is_absent = any(
                        abs.employee_id == emp.id and abs.overlaps_date(d)
                        for abs in absences
                    )
                    if not is_absent and (emp.id, d) in employee_active:
                        weekday_vars.append(employee_active[(emp.id, d)])
                
                if len(weekday_vars) == 5:
                    # Create a bonus variable: if all 5 weekdays are worked, bonus = 1
                    mon_fri_bonus = model.NewBoolVar(f'mon_fri_bonus_e{emp.id}_w{week_idx}')
                    # mon_fri_bonus == 1 if sum(weekday_vars) == 5
                    model.Add(sum(weekday_vars) >= 5).OnlyEnforceIf(mon_fri_bonus)
                    model.Add(sum(weekday_vars) < 5).OnlyEnforceIf(mon_fri_bonus.Not())
                    objective_vars.append(mon_fri_bonus)
            
            # Objective 2: Encourage Sat-Sun blocks
            if len(weekend_days) == 2:
                sat = weekend_days[0] if weekend_days[0].weekday() == 5 else weekend_days[1]
                sun = weekend_days[1] if weekend_days[1].weekday() == 6 else weekend_days[0]
                
                sat_absent = any(
                    abs.employee_id == emp.id and abs.overlaps_date(sat)
                    for abs in absences
                )
                sun_absent = any(
                    abs.employee_id == emp.id and abs.overlaps_date(sun)
                    for abs in absences
                )
                
                if not sat_absent and not sun_absent:
                    if (emp.id, sat) in employee_weekend_shift and (emp.id, sun) in employee_weekend_shift:
                        # Create a bonus variable: if both Sat and Sun are worked, bonus = 1
                        sat_sun_bonus = model.NewBoolVar(f'sat_sun_bonus_e{emp.id}_w{week_idx}')
                        # sat_sun_bonus == 1 if both worked
                        sat_var = employee_weekend_shift[(emp.id, sat)]
                        sun_var = employee_weekend_shift[(emp.id, sun)]
                        model.Add(sat_var + sun_var >= 2).OnlyEnforceIf(sat_sun_bonus)
                        model.Add(sat_var + sun_var < 2).OnlyEnforceIf(sat_sun_bonus.Not())
                        objective_vars.append(sat_sun_bonus)
    
    return objective_vars


