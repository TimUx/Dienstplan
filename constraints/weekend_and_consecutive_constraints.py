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


def add_weekly_shift_type_limit_constraints(
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
    max_shift_types_per_week: int = 2
):
    """
    SOFT CONSTRAINT: Limit the number of different shift types an employee works in a week.
    
    Requirement from practical examples:
    - Employees should not have more than 2 different shift types in a week
    - Examples of violations:
      * Lisa Meyer: S-N-N-F-F-F-F in first week (3 types: S, N, F)
      * Julia Becker: F-N-N-S-S in one week (3 types: F, N, S)
    
    Implementation:
    - For each employee and each week, count the number of distinct shift types worked
    - Penalize if more than max_shift_types_per_week (default: 2)
    - High penalty (500 points per violation) to strongly discourage this
    
    Args:
        max_shift_types_per_week: Maximum number of different shift types allowed per week
    
    Returns:
        List of penalty variables for shift type diversity violations
    """
    diversity_penalties = []
    
    # High penalty for having too many shift types in a week
    DIVERSITY_PENALTY = 500
    
    # Pre-compute date-to-week mapping
    date_to_week = {}
    for week_idx, week_dates in enumerate(weeks):
        for d in week_dates:
            date_to_week[d] = week_idx
    
    # Pre-compute employee-to-team mapping
    emp_to_team = {}
    for emp in employees:
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    emp_to_team[emp.id] = team
                    break
    
    for emp in employees:
        if not emp.team_id:
            continue
        
        for week_idx, week_dates in enumerate(weeks):
            # For each shift type, create a boolean: does employee work this shift type this week?
            shift_type_worked = {}
            
            for shift_code in shift_codes:
                # Create boolean variable: did employee work this shift type at least once this week?
                has_shift_type = model.NewBoolVar(f"week_shift_type_{emp.id}_{week_idx}_{shift_code}")
                shift_instances = []
                
                for d in week_dates:
                    # Check team-based shifts (weekday)
                    if d.weekday() < 5 and (emp.id, d) in employee_active:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, shift_code) in team_shift:
                            # Employee works this shift if: active AND team has this shift
                            shift_work = model.NewBoolVar(f"team_shift_{emp.id}_{d}_{shift_code}")
                            model.AddMultiplicationEquality(
                                shift_work,
                                [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            shift_instances.append(shift_work)
                    
                    # Check team-based shifts (weekend)
                    if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, shift_code) in team_shift:
                            shift_weekend = model.NewBoolVar(f"team_weekend_{emp.id}_{d}_{shift_code}")
                            model.AddMultiplicationEquality(
                                shift_weekend,
                                [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            shift_instances.append(shift_weekend)
                    
                    # Check cross-team shifts (weekday)
                    if d.weekday() < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        shift_instances.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    
                    # Check cross-team shifts (weekend)
                    if d.weekday() >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        shift_instances.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                # has_shift_type = 1 if any instance of this shift type exists this week
                if shift_instances:
                    model.Add(sum(shift_instances) >= 1).OnlyEnforceIf(has_shift_type)
                    model.Add(sum(shift_instances) == 0).OnlyEnforceIf(has_shift_type.Not())
                else:
                    model.Add(has_shift_type == 0)
                
                shift_type_worked[shift_code] = has_shift_type
            
            # Count total number of different shift types worked this week
            if shift_type_worked:
                num_shift_types = model.NewIntVar(0, len(shift_codes), f"num_shift_types_{emp.id}_{week_idx}")
                model.Add(num_shift_types == sum(shift_type_worked.values()))
                
                # Create violation variable: num_shift_types > max_shift_types_per_week
                violation = model.NewBoolVar(f"shift_diversity_viol_{emp.id}_{week_idx}")
                model.Add(num_shift_types > max_shift_types_per_week).OnlyEnforceIf(violation)
                model.Add(num_shift_types <= max_shift_types_per_week).OnlyEnforceIf(violation.Not())
                
                # Add penalty
                penalty = model.NewIntVar(0, DIVERSITY_PENALTY, f"shift_diversity_pen_{emp.id}_{week_idx}")
                model.AddMultiplicationEquality(penalty, [violation, DIVERSITY_PENALTY])
                diversity_penalties.append(penalty)
    
    return diversity_penalties


def add_weekend_shift_consistency_constraints(
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
    shift_codes: List[str]
):
    """
    SOFT CONSTRAINT: Prevent shift type changes within weekends.
    
    Requirement from practical examples:
    - If an employee works on Friday and then on Saturday/Sunday, they should work the same shift type
    - Examples of violations:
      * Robert Franke: Early (Friday) → Night (Saturday)
      * Nicole Schröder: Early (Friday) → Late (Saturday)
    
    Implementation:
    - For each week, check if Friday shift type matches Saturday/Sunday shift types
    - Penalize mismatches to encourage consistency
    - Medium-high penalty (300 points per mismatch)
    
    Returns:
        List of penalty variables for weekend shift consistency violations
    """
    weekend_consistency_penalties = []
    
    # Penalty for shift type changes from Friday to weekend
    WEEKEND_CONSISTENCY_PENALTY = 300
    
    # Pre-compute employee-to-team mapping
    emp_to_team = {}
    for emp in employees:
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    emp_to_team[emp.id] = team
                    break
    
    for emp in employees:
        if not emp.team_id:
            continue
        
        for week_idx, week_dates in enumerate(weeks):
            # Find Friday, Saturday, and Sunday in this week
            friday = None
            saturday = None
            sunday = None
            
            for d in week_dates:
                if d.weekday() == 4:  # Friday
                    friday = d
                elif d.weekday() == 5:  # Saturday
                    saturday = d
                elif d.weekday() == 6:  # Sunday
                    sunday = d
            
            if not friday:
                continue  # No Friday in this week (shouldn't happen with full weeks)
            
            # For each shift type, determine if employee works it on Friday
            friday_shift_vars = {}
            for shift_code in shift_codes:
                shift_instances = []
                
                # Friday is a weekday, check employee_active
                if (emp.id, friday) in employee_active:
                    team = emp_to_team.get(emp.id)
                    if team and (team.id, week_idx, shift_code) in team_shift:
                        # Employee works this shift on Friday if: active AND team has this shift
                        friday_work = model.NewBoolVar(f"friday_{emp.id}_{week_idx}_{shift_code}")
                        model.AddMultiplicationEquality(
                            friday_work,
                            [employee_active[(emp.id, friday)], team_shift[(team.id, week_idx, shift_code)]]
                        )
                        shift_instances.append(friday_work)
                
                # Check cross-team Friday work
                if (emp.id, friday, shift_code) in employee_cross_team_shift:
                    shift_instances.append(employee_cross_team_shift[(emp.id, friday, shift_code)])
                
                if shift_instances:
                    # Track whether employee works this specific shift type on Friday
                    friday_works_shift_type = model.NewBoolVar(f"has_friday_{emp.id}_{week_idx}_{shift_code}")
                    model.Add(sum(shift_instances) >= 1).OnlyEnforceIf(friday_works_shift_type)
                    model.Add(sum(shift_instances) == 0).OnlyEnforceIf(friday_works_shift_type.Not())
                    friday_shift_vars[shift_code] = friday_works_shift_type
            
            # For Saturday and Sunday, check if shift type matches Friday
            for weekend_day in [saturday, sunday]:
                if not weekend_day:
                    continue
                
                for shift_code in shift_codes:
                    weekend_shift_instances = []
                    
                    # Weekend day - check employee_weekend_shift
                    if (emp.id, weekend_day) in employee_weekend_shift:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, shift_code) in team_shift:
                            weekend_work = model.NewBoolVar(f"weekend_{emp.id}_{weekend_day}_{shift_code}")
                            model.AddMultiplicationEquality(
                                weekend_work,
                                [employee_weekend_shift[(emp.id, weekend_day)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            weekend_shift_instances.append(weekend_work)
                    
                    # Check cross-team weekend work
                    if (emp.id, weekend_day, shift_code) in employee_cross_team_weekend:
                        weekend_shift_instances.append(employee_cross_team_weekend[(emp.id, weekend_day, shift_code)])
                    
                    if weekend_shift_instances:
                        # Track whether employee works this specific shift type on weekend day
                        weekend_works_shift_type = model.NewBoolVar(f"has_weekend_{emp.id}_{weekend_day}_{shift_code}")
                        model.Add(sum(weekend_shift_instances) >= 1).OnlyEnforceIf(weekend_works_shift_type)
                        model.Add(sum(weekend_shift_instances) == 0).OnlyEnforceIf(weekend_works_shift_type.Not())
                        
                        # Check for mismatch: different shift types on Friday vs weekend day
                        # Violation occurs if:
                        # - Employee works on both days (Friday and weekend_day)
                        # - But with different shift types
                        
                        # For each OTHER shift type (different from current)
                        for other_shift_code in shift_codes:
                            if other_shift_code == shift_code:
                                continue  # Same shift type - no mismatch
                            
                            if other_shift_code in friday_shift_vars:
                                # Mismatch: Friday has other_shift_code, weekend has shift_code
                                mismatch = model.NewBoolVar(f"weekend_mismatch_{emp.id}_{weekend_day}_{other_shift_code}_{shift_code}")
                                model.AddBoolAnd([friday_shift_vars[other_shift_code], weekend_works_shift_type]).OnlyEnforceIf(mismatch)
                                model.AddBoolOr([friday_shift_vars[other_shift_code].Not(), weekend_works_shift_type.Not()]).OnlyEnforceIf(mismatch.Not())
                                
                                # Add penalty for mismatch
                                penalty = model.NewIntVar(0, WEEKEND_CONSISTENCY_PENALTY, f"weekend_pen_{emp.id}_{weekend_day}_{other_shift_code}_{shift_code}")
                                model.AddMultiplicationEquality(penalty, [mismatch, WEEKEND_CONSISTENCY_PENALTY])
                                weekend_consistency_penalties.append(penalty)
    
    return weekend_consistency_penalties


def add_team_night_shift_consistency_constraints(
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
    shift_codes: List[str]
):
    """
    SOFT CONSTRAINT: Strongly discourage cross-team night shifts when employee's team is not on night shift.
    
    Requirement from practical examples:
    - Night shifts should preferably stay within teams that are on night shift rotation
    - Example violations:
      * Anna Schmidt (Team Alpha, week with late shift) worked night shifts cross-team
      * Should have been assigned to Maria Lange or Nicole Schröder (Team Gamma, on night shift)
    
    Implementation:
    - For each employee working a cross-team night shift, check if their own team has night shift that week
    - If own team does NOT have night shift but employee works night shift cross-team, apply penalty
    - Very high penalty (600 points) to strongly discourage this pattern
    
    Returns:
        List of penalty variables for cross-team night shift violations
    """
    night_team_consistency_penalties = []
    
    # Very high penalty for cross-team night shifts when own team is not on night shift
    NIGHT_TEAM_PENALTY = 600
    
    # Pre-compute employee-to-team mapping
    emp_to_team = {}
    for emp in employees:
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    emp_to_team[emp.id] = team
                    break
    
    for emp in employees:
        if not emp.team_id:
            continue
        
        team = emp_to_team.get(emp.id)
        if not team:
            continue
        
        for week_idx, week_dates in enumerate(weeks):
            # Check if employee's team has night shift this week
            team_has_night = None
            if (team.id, week_idx, 'N') in team_shift:
                team_has_night = team_shift[(team.id, week_idx, 'N')]
            
            if team_has_night is None:
                continue  # Skip if we can't determine team's night shift status
            
            # Check if employee works cross-team night shifts this week
            for d in week_dates:
                cross_team_night_vars = []
                
                # Check weekday cross-team night shift
                if d.weekday() < 5 and (emp.id, d, 'N') in employee_cross_team_shift:
                    cross_team_night_vars.append(employee_cross_team_shift[(emp.id, d, 'N')])
                
                # Check weekend cross-team night shift
                if d.weekday() >= 5 and (emp.id, d, 'N') in employee_cross_team_weekend:
                    cross_team_night_vars.append(employee_cross_team_weekend[(emp.id, d, 'N')])
                
                if not cross_team_night_vars:
                    continue
                
                # Check if employee works cross-team night shift when own team is NOT on night shift
                # Violation = (employee works cross-team night shift) AND (team does NOT have night shift)
                for cross_team_night in cross_team_night_vars:
                    # Create violation: cross_team_night=1 AND team_has_night=0
                    violation = model.NewBoolVar(f"night_team_viol_{emp.id}_{d}")
                    model.AddBoolAnd([cross_team_night, team_has_night.Not()]).OnlyEnforceIf(violation)
                    model.AddBoolOr([cross_team_night.Not(), team_has_night]).OnlyEnforceIf(violation.Not())
                    
                    # Add penalty
                    penalty = model.NewIntVar(0, NIGHT_TEAM_PENALTY, f"night_team_pen_{emp.id}_{d}")
                    model.AddMultiplicationEquality(penalty, [violation, NIGHT_TEAM_PENALTY])
                    night_team_consistency_penalties.append(penalty)
    
    return night_team_consistency_penalties


def add_consecutive_shifts_constraints(
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
    previous_employee_shifts: Dict[Tuple[int, date], str] = None
):
    """
    HARD CONSTRAINT (within period) + SOFT (cross-month boundary):
    Limit consecutive working days per shift type and across all shift types.
    
    Requirements (updated to enforce cross-shift-type limits and cross-month boundaries):
    - Each shift type defines its own maximum consecutive working days
    - After reaching this limit for a shift type, employee MUST have 24h break before working ANY shift
    - This ensures proper rest periods even when switching between shift types
    - IMPORTANT: Checks shifts from BEFORE the planning period to catch violations across month boundaries
    
    Example:
    - S shift has max_consecutive_days=6, N shift has max_consecutive_days=3
    - Employee works 6x S shift → must have 1 day off before working ANY shift (S, F, or N)
    - Employee works 3x N shift → must have 1 day off before working ANY shift (S, F, or N)
    
    Cross-month boundary example:
    - Employee works 4 shifts at end of January (Jan 28-31)
    - Employee plans to work 4 shifts at start of February (Feb 1-4)
    - Total: 8 consecutive days → VIOLATION detected using previous_employee_shifts
    
    Implementation:
    - WITHIN-PERIOD: Hard constraints (model.Add) that the solver cannot override
      - Per-shift-type: In any (max+1)-day window, sum(shift_indicators) <= max_consecutive_days
      - Cross-shift-type: After max consecutive days of shift X, day (max+1) must have NO work at all
      - Total consecutive: In any (max+1)-day window, sum(any_shift) <= max_total_consecutive
    - CROSS-MONTH BOUNDARY: Soft high-penalty constraints (50,000 per violation)
      - Cannot be made hard since previous month data is immutable
    
    Args:
        shift_types: List of shift types with their max_consecutive_days settings
        previous_employee_shifts: Dict mapping (emp_id, date) -> shift_code for dates BEFORE planning period.
                                 Used to check consecutive shifts across month boundaries.
    
    Returns:
        List of penalty variables for cross-month boundary violations only
    """
    consecutive_violation_penalties = []
    
    # Build a mapping from shift code to shift type
    shift_code_to_type = {st.code: st for st in shift_types}
    
    # Pre-compute date-to-week mapping for efficiency
    date_to_week = {}
    for week_idx, week_dates in enumerate(weeks):
        for d in week_dates:
            date_to_week[d] = week_idx
    
    # Pre-compute employee-to-team mapping for efficiency
    emp_to_team = {}
    for emp in employees:
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    emp_to_team[emp.id] = team
                    break
    
    # Initialize previous_employee_shifts if not provided
    if previous_employee_shifts is None:
        previous_employee_shifts = {}
    
    # Get the maximum consecutive days across all shift types (for lookback)
    max_consecutive_limit = max((st.max_consecutive_days for st in shift_types), default=7)
    
    # Build a map of previous shifts by employee for quick lookup
    # We need to look back up to max_consecutive_limit days before the planning period
    from datetime import timedelta
    first_planning_date = dates[0] if dates else None
    previous_shifts_by_emp = {}
    if first_planning_date:
        for emp in employees:
            emp_previous_shifts = []
            # Look back up to max_consecutive_limit days
            for days_back in range(1, max_consecutive_limit + 1):
                check_date = first_planning_date - timedelta(days=days_back)
                if (emp.id, check_date) in previous_employee_shifts:
                    emp_previous_shifts.append((check_date, previous_employee_shifts[(emp.id, check_date)]))
            # Sort by date (oldest first)
            emp_previous_shifts.sort(key=lambda x: x[0])
            if emp_previous_shifts:
                previous_shifts_by_emp[emp.id] = emp_previous_shifts
    
    # For each employee and each shift type, check consecutive working days
    for emp in employees:
        for shift_code in shift_codes:
            # Get the shift type's max consecutive days setting
            shift_type = shift_code_to_type.get(shift_code)
            if not shift_type:
                continue
            
            max_consecutive_days = shift_type.max_consecutive_days
            
            # Penalty weight for cross-month boundary violations.
            # These cannot be made hard (previous month data is immutable), but are
            # given a very high penalty to strongly discourage extending violations.
            # Weight: 50,000 per violation (much higher than any other soft constraint)
            consecutive_penalty_weight = CROSS_MONTH_BOUNDARY_PENALTY
            
            # CROSS-MONTH BOUNDARY CHECK:
            # Check if employee has consecutive shifts from BEFORE the planning period
            # that extend into the beginning of the planning period, creating a violation.
            # This catches cases like: 4 shifts at end of Jan + 4 shifts at start of Feb = 8 consecutive days
            if emp.id in previous_shifts_by_emp and len(dates) > 0:
                prev_shifts = previous_shifts_by_emp[emp.id]
                
                # Count consecutive CALENDAR days of this shift type leading up to the planning period
                # We need to check that days are actually consecutive (no gaps)
                consecutive_count = 0
                last_date_checked = first_planning_date - timedelta(days=1)  # Day before planning period
                
                # Work backwards from the day before planning period
                for days_back in range(1, max_consecutive_limit + 1):
                    check_date = first_planning_date - timedelta(days=days_back)
                    
                    # Check if employee worked this shift on this date
                    worked_this_shift = False
                    for prev_date, prev_shift_code in prev_shifts:
                        if prev_date == check_date and prev_shift_code == shift_code:
                            worked_this_shift = True
                            break
                    
                    if worked_this_shift:
                        consecutive_count += 1
                    else:
                        # Chain broken - no shift on this date
                        break
                
                # If we have consecutive shifts leading up to the planning period,
                # check if continuing them into the planning period would violate the limit
                if consecutive_count > 0:
                    # Check windows starting from the beginning of the planning period
                    # We need to detect ANY violation where total consecutive days > max_consecutive_days
                    # Example: 4 prev days, max=6
                    # - Check 3 more days: 4+3=7 > 6 → violation
                    # - Check 4 more days: 4+4=8 > 6 → violation
                    # - etc.
                    # We should check up to enough days to catch all violations
                    # But limit to a reasonable number (e.g., 2 * max_consecutive_days)
                    max_check_days = min(2 * max_consecutive_days, len(dates))
                    
                    for num_days_in_period in range(1, max_check_days + 1):
                        # Build indicators for the days in the planning period
                        period_shift_indicators = []
                        
                        for day_idx in range(num_days_in_period):
                            current_date = dates[day_idx]
                            week_idx = date_to_week.get(current_date)
                            
                            if week_idx is None:
                                zero_var = model.NewBoolVar(f"prev_zero_{shift_code}_{emp.id}_{day_idx}")
                                model.Add(zero_var == 0)
                                period_shift_indicators.append(zero_var)
                                continue
                            
                            # Collect variables for this specific shift type (same logic as below)
                            shift_vars = []
                            
                            if current_date.weekday() < 5 and (emp.id, current_date) in employee_active:
                                team = emp_to_team.get(emp.id)
                                if team and (team.id, week_idx, shift_code) in team_shift:
                                    shift_work = model.NewBoolVar(f"prev_{shift_code}_team_{emp.id}_{day_idx}")
                                    model.AddMultiplicationEquality(
                                        shift_work,
                                        [employee_active[(emp.id, current_date)], team_shift[(team.id, week_idx, shift_code)]]
                                    )
                                    shift_vars.append(shift_work)
                            
                            if current_date.weekday() >= 5 and (emp.id, current_date) in employee_weekend_shift:
                                team = emp_to_team.get(emp.id)
                                if team and (team.id, week_idx, shift_code) in team_shift:
                                    shift_weekend = model.NewBoolVar(f"prev_{shift_code}_weekend_{emp.id}_{day_idx}")
                                    model.AddMultiplicationEquality(
                                        shift_weekend,
                                        [employee_weekend_shift[(emp.id, current_date)], team_shift[(team.id, week_idx, shift_code)]]
                                    )
                                    shift_vars.append(shift_weekend)
                            
                            if (emp.id, current_date, shift_code) in employee_cross_team_shift:
                                shift_vars.append(employee_cross_team_shift[(emp.id, current_date, shift_code)])
                            if (emp.id, current_date, shift_code) in employee_cross_team_weekend:
                                shift_vars.append(employee_cross_team_weekend[(emp.id, current_date, shift_code)])
                            
                            if shift_vars:
                                is_shift = model.NewBoolVar(f"prev_is_{shift_code}_{emp.id}_{day_idx}")
                                model.Add(sum(shift_vars) >= 1).OnlyEnforceIf(is_shift)
                                model.Add(sum(shift_vars) == 0).OnlyEnforceIf(is_shift.Not())
                                period_shift_indicators.append(is_shift)
                            else:
                                zero_var = model.NewBoolVar(f"prev_zero_{shift_code}_{emp.id}_{day_idx}")
                                model.Add(zero_var == 0)
                                period_shift_indicators.append(zero_var)
                        
                        # Check if all days in this window have the shift type
                        # Total consecutive = consecutive_count (from previous) + num_days_in_period (from current)
                        total_consecutive = consecutive_count + num_days_in_period
                        
                        if total_consecutive > max_consecutive_days and len(period_shift_indicators) == num_days_in_period:
                            # Violation if all days in the planning period portion have this shift
                            all_shifts_in_period = model.NewBoolVar(f"prev_all_{shift_code}_{emp.id}_{num_days_in_period}")
                            model.Add(sum(period_shift_indicators) == num_days_in_period).OnlyEnforceIf(all_shifts_in_period)
                            model.Add(sum(period_shift_indicators) < num_days_in_period).OnlyEnforceIf(all_shifts_in_period.Not())
                            
                            # High-weight soft penalty for cross-month boundary violations (50,000)
                            prev_penalty = model.NewIntVar(0, consecutive_penalty_weight, f"prev_{shift_code}_penalty_{emp.id}_{num_days_in_period}")
                            model.AddMultiplicationEquality(prev_penalty, [all_shifts_in_period, consecutive_penalty_weight])
                            consecutive_violation_penalties.append(prev_penalty)
            
            # Check consecutive days for this specific shift type
            for start_idx in range(len(dates) - max_consecutive_days):
                shift_indicators = []
                
                for day_offset in range(max_consecutive_days + 1):
                    date_idx = start_idx + day_offset
                    current_date = dates[date_idx]
                    
                    # Get week index from pre-computed mapping
                    week_idx = date_to_week.get(current_date)
                    if week_idx is None:
                        shift_indicators.append(0)
                        continue
                    
                    # Collect variables for this specific shift type
                    shift_vars = []
                    
                    # Team-based shift (weekday)
                    if current_date.weekday() < 5 and (emp.id, current_date) in employee_active:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, shift_code) in team_shift:
                            # Employee works this shift if: active AND team has this shift
                            shift_work = model.NewBoolVar(f"{shift_code}_team_{emp.id}_{date_idx}")
                            model.AddMultiplicationEquality(
                                shift_work,
                                [employee_active[(emp.id, current_date)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            shift_vars.append(shift_work)
                    
                    # Team-based shift (weekend)
                    if current_date.weekday() >= 5 and (emp.id, current_date) in employee_weekend_shift:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, shift_code) in team_shift:
                            shift_weekend = model.NewBoolVar(f"{shift_code}_weekend_{emp.id}_{date_idx}")
                            model.AddMultiplicationEquality(
                                shift_weekend,
                                [employee_weekend_shift[(emp.id, current_date)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            shift_vars.append(shift_weekend)
                    
                    # Cross-team shift
                    if (emp.id, current_date, shift_code) in employee_cross_team_shift:
                        shift_vars.append(employee_cross_team_shift[(emp.id, current_date, shift_code)])
                    if (emp.id, current_date, shift_code) in employee_cross_team_weekend:
                        shift_vars.append(employee_cross_team_weekend[(emp.id, current_date, shift_code)])
                    
                    if shift_vars:
                        is_shift = model.NewBoolVar(f"is_{shift_code}_{emp.id}_{date_idx}")
                        model.Add(sum(shift_vars) >= 1).OnlyEnforceIf(is_shift)
                        model.Add(sum(shift_vars) == 0).OnlyEnforceIf(is_shift.Not())
                        shift_indicators.append(is_shift)
                    else:
                        # Create a BoolVar constrained to 0 instead of appending literal 0
                        # This ensures all elements in shift_indicators are BoolVars for proper CP-SAT constraint handling
                        zero_var = model.NewBoolVar(f"zero_{shift_code}_{emp.id}_{date_idx}")
                        model.Add(zero_var == 0)
                        shift_indicators.append(zero_var)
                
                # HARD CONSTRAINT: At most max_consecutive_days of this shift type in any (max+1)-day window
                if len(shift_indicators) == max_consecutive_days + 1:
                    model.Add(sum(shift_indicators) <= max_consecutive_days)
                    
                    # CROSS-SHIFT-TYPE ENFORCEMENT (HARD):
                    # After working max_consecutive_days of shift_code, employee must have a break
                    # before working ANY shift type (not just the same shift type)
                    # This enforces: 6x S → break, even if next day would be F or N
                    #                3x N → break, even if next day would be F or S
                    # Check if first max_consecutive_days are all this shift type
                    first_n_days_this_shift = model.NewBoolVar(f"{shift_code}_first_{max_consecutive_days}_{emp.id}_{start_idx}")
                    model.Add(sum(shift_indicators[:max_consecutive_days]) == max_consecutive_days).OnlyEnforceIf(first_n_days_this_shift)
                    model.Add(sum(shift_indicators[:max_consecutive_days]) < max_consecutive_days).OnlyEnforceIf(first_n_days_this_shift.Not())
                    
                    # Check if employee works ANY shift on day (max_consecutive_days + 1)
                    last_day_idx = start_idx + max_consecutive_days
                    if last_day_idx < len(dates):
                        last_date = dates[last_day_idx]
                        last_week_idx = date_to_week.get(last_date)
                        
                        # Collect all shift indicators for the last day (ANY shift type)
                        any_shift_last_day_vars = []
                        
                        for check_shift_code in shift_codes:
                            check_shift_vars = []
                            
                            # Team-based shift (weekday)
                            if last_date.weekday() < 5 and (emp.id, last_date) in employee_active:
                                team = emp_to_team.get(emp.id)
                                if team and last_week_idx is not None and (team.id, last_week_idx, check_shift_code) in team_shift:
                                    check_work = model.NewBoolVar(f"cross_check_{check_shift_code}_team_{emp.id}_{last_day_idx}")
                                    model.AddMultiplicationEquality(
                                        check_work,
                                        [employee_active[(emp.id, last_date)], team_shift[(team.id, last_week_idx, check_shift_code)]]
                                    )
                                    check_shift_vars.append(check_work)
                            
                            # Team-based shift (weekend)
                            if last_date.weekday() >= 5 and (emp.id, last_date) in employee_weekend_shift:
                                team = emp_to_team.get(emp.id)
                                if team and last_week_idx is not None and (team.id, last_week_idx, check_shift_code) in team_shift:
                                    check_weekend = model.NewBoolVar(f"cross_check_{check_shift_code}_weekend_{emp.id}_{last_day_idx}")
                                    model.AddMultiplicationEquality(
                                        check_weekend,
                                        [employee_weekend_shift[(emp.id, last_date)], team_shift[(team.id, last_week_idx, check_shift_code)]]
                                    )
                                    check_shift_vars.append(check_weekend)
                            
                            # Cross-team shift
                            if (emp.id, last_date, check_shift_code) in employee_cross_team_shift:
                                check_shift_vars.append(employee_cross_team_shift[(emp.id, last_date, check_shift_code)])
                            if (emp.id, last_date, check_shift_code) in employee_cross_team_weekend:
                                check_shift_vars.append(employee_cross_team_weekend[(emp.id, last_date, check_shift_code)])
                            
                            if check_shift_vars:
                                has_shift = model.NewBoolVar(f"cross_has_{check_shift_code}_{emp.id}_{last_day_idx}")
                                model.Add(sum(check_shift_vars) >= 1).OnlyEnforceIf(has_shift)
                                model.Add(sum(check_shift_vars) == 0).OnlyEnforceIf(has_shift.Not())
                                any_shift_last_day_vars.append(has_shift)
                        
                        if any_shift_last_day_vars:
                            # HARD: If first N days are all this shift type, last day must have no work at all
                            works_any_shift_last_day = model.NewBoolVar(f"cross_any_shift_{emp.id}_{last_day_idx}")
                            model.Add(sum(any_shift_last_day_vars) >= 1).OnlyEnforceIf(works_any_shift_last_day)
                            model.Add(sum(any_shift_last_day_vars) == 0).OnlyEnforceIf(works_any_shift_last_day.Not())
                            
                            # Hard enforcement: after max_consecutive_days of this shift, day (max+1) must be free
                            model.Add(works_any_shift_last_day == 0).OnlyEnforceIf(first_n_days_this_shift)
    
    # TOTAL CONSECUTIVE WORKING DAYS CONSTRAINT:
    # Enforce maximum total consecutive working days across ALL shift types.
    # This prevents scenarios like: 5x S + 3x N = 8 consecutive days
    # where neither shift type individually violates its limit, but total is too high.
    #
    # Use the maximum max_consecutive_days value across all shift types as the global limit.
    # This ensures employees don't work more than the highest allowed consecutive days,
    # regardless of shift type combinations.
    max_total_consecutive = max((st.max_consecutive_days for st in shift_types), default=6)
    
    for emp in employees:
        # CROSS-MONTH BOUNDARY CHECK FOR TOTAL CONSECUTIVE DAYS:
        # Check if employee has consecutive days (any shift type) from BEFORE the planning period
        if emp.id in previous_shifts_by_emp and len(dates) > 0:
            prev_shifts = previous_shifts_by_emp[emp.id]
            
            # Count consecutive working CALENDAR days (any shift type) leading up to the planning period
            # We need to check that days are actually consecutive (no gaps)
            consecutive_work_days = 0
            
            # Work backwards from the day before planning period
            for days_back in range(1, max_consecutive_limit + 1):
                check_date = first_planning_date - timedelta(days=days_back)
                
                # Check if employee worked ANY shift on this date
                worked_any_shift = False
                for prev_date, prev_shift_code in prev_shifts:
                    if prev_date == check_date:
                        worked_any_shift = True
                        break
                
                if worked_any_shift:
                    consecutive_work_days += 1
                else:
                    # Chain broken - no shift on this date
                    break
            
            # If we have consecutive working days leading up to the planning period,
            # check if continuing them into the planning period would violate the limit
            if consecutive_work_days > 0:
                max_check_days = min(2 * max_total_consecutive, len(dates))
                
                for num_days_in_period in range(1, max_check_days + 1):
                    # Build indicators for ANY shift on each day in the planning period
                    period_any_shift_indicators = []
                    
                    for day_idx in range(num_days_in_period):
                        current_date = dates[day_idx]
                        week_idx = date_to_week.get(current_date)
                        
                        if week_idx is None:
                            zero_var = model.NewBoolVar(f"prev_total_zero_{emp.id}_{day_idx}")
                            model.Add(zero_var == 0)
                            period_any_shift_indicators.append(zero_var)
                            continue
                        
                        # Collect ALL shift variables for this day (ANY shift type)
                        day_shift_vars = []
                        
                        for check_shift_code in shift_codes:
                            if current_date.weekday() < 5 and (emp.id, current_date) in employee_active:
                                team = emp_to_team.get(emp.id)
                                if team and (team.id, week_idx, check_shift_code) in team_shift:
                                    work_var = model.NewBoolVar(f"prev_total_{check_shift_code}_team_{emp.id}_{day_idx}")
                                    model.AddMultiplicationEquality(
                                        work_var,
                                        [employee_active[(emp.id, current_date)], team_shift[(team.id, week_idx, check_shift_code)]]
                                    )
                                    day_shift_vars.append(work_var)
                            
                            if current_date.weekday() >= 5 and (emp.id, current_date) in employee_weekend_shift:
                                team = emp_to_team.get(emp.id)
                                if team and (team.id, week_idx, check_shift_code) in team_shift:
                                    weekend_var = model.NewBoolVar(f"prev_total_{check_shift_code}_weekend_{emp.id}_{day_idx}")
                                    model.AddMultiplicationEquality(
                                        weekend_var,
                                        [employee_weekend_shift[(emp.id, current_date)], team_shift[(team.id, week_idx, check_shift_code)]]
                                    )
                                    day_shift_vars.append(weekend_var)
                            
                            if (emp.id, current_date, check_shift_code) in employee_cross_team_shift:
                                day_shift_vars.append(employee_cross_team_shift[(emp.id, current_date, check_shift_code)])
                            if (emp.id, current_date, check_shift_code) in employee_cross_team_weekend:
                                day_shift_vars.append(employee_cross_team_weekend[(emp.id, current_date, check_shift_code)])
                        
                        # Create indicator: does employee work ANY shift on this day?
                        if day_shift_vars:
                            works_any = model.NewBoolVar(f"prev_total_any_{emp.id}_{day_idx}")
                            model.Add(sum(day_shift_vars) >= 1).OnlyEnforceIf(works_any)
                            model.Add(sum(day_shift_vars) == 0).OnlyEnforceIf(works_any.Not())
                            period_any_shift_indicators.append(works_any)
                        else:
                            zero_var = model.NewBoolVar(f"prev_total_zero_{emp.id}_{day_idx}")
                            model.Add(zero_var == 0)
                            period_any_shift_indicators.append(zero_var)
                    
                    # Check if all days in this window have work
                    # Total consecutive = consecutive_work_days (from previous) + num_days_in_period (from current)
                    total_consecutive = consecutive_work_days + num_days_in_period
                    
                    if total_consecutive > max_total_consecutive and len(period_any_shift_indicators) == num_days_in_period:
                        # Violation if all days in the planning period portion have work
                        all_work_in_period = model.NewBoolVar(f"prev_total_all_{emp.id}_{num_days_in_period}")
                        model.Add(sum(period_any_shift_indicators) == num_days_in_period).OnlyEnforceIf(all_work_in_period)
                        model.Add(sum(period_any_shift_indicators) < num_days_in_period).OnlyEnforceIf(all_work_in_period.Not())
                        
                        # High-weight soft penalty for cross-month boundary violations
                        prev_total_penalty = model.NewIntVar(0, CROSS_MONTH_BOUNDARY_PENALTY, f"prev_total_penalty_{emp.id}_{num_days_in_period}")
                        model.AddMultiplicationEquality(prev_total_penalty, [all_work_in_period, CROSS_MONTH_BOUNDARY_PENALTY])
                        consecutive_violation_penalties.append(prev_total_penalty)
        
        # HARD CONSTRAINT: Check each possible window of (max_total_consecutive + 1) days
        for start_idx in range(len(dates) - max_total_consecutive):
            any_shift_indicators = []
            
            for day_offset in range(max_total_consecutive + 1):
                date_idx = start_idx + day_offset
                current_date = dates[date_idx]
                
                # Get week index
                week_idx = date_to_week.get(current_date)
                if week_idx is None:
                    # Create zero variable for consistency
                    zero_var = model.NewBoolVar(f"total_zero_{emp.id}_{date_idx}")
                    model.Add(zero_var == 0)
                    any_shift_indicators.append(zero_var)
                    continue
                
                # Collect ALL shift variables for this day (ANY shift type)
                day_shift_vars = []
                
                for check_shift_code in shift_codes:
                    # Team-based shift (weekday)
                    if current_date.weekday() < 5 and (emp.id, current_date) in employee_active:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, check_shift_code) in team_shift:
                            work_var = model.NewBoolVar(f"total_check_{check_shift_code}_team_{emp.id}_{date_idx}")
                            model.AddMultiplicationEquality(
                                work_var,
                                [employee_active[(emp.id, current_date)], team_shift[(team.id, week_idx, check_shift_code)]]
                            )
                            day_shift_vars.append(work_var)
                    
                    # Team-based shift (weekend)
                    if current_date.weekday() >= 5 and (emp.id, current_date) in employee_weekend_shift:
                        team = emp_to_team.get(emp.id)
                        if team and (team.id, week_idx, check_shift_code) in team_shift:
                            weekend_var = model.NewBoolVar(f"total_check_{check_shift_code}_weekend_{emp.id}_{date_idx}")
                            model.AddMultiplicationEquality(
                                weekend_var,
                                [employee_weekend_shift[(emp.id, current_date)], team_shift[(team.id, week_idx, check_shift_code)]]
                            )
                            day_shift_vars.append(weekend_var)
                    
                    # Cross-team shift
                    if (emp.id, current_date, check_shift_code) in employee_cross_team_shift:
                        day_shift_vars.append(employee_cross_team_shift[(emp.id, current_date, check_shift_code)])
                    if (emp.id, current_date, check_shift_code) in employee_cross_team_weekend:
                        day_shift_vars.append(employee_cross_team_weekend[(emp.id, current_date, check_shift_code)])
                
                # Create indicator: does employee work ANY shift on this day?
                if day_shift_vars:
                    works_any = model.NewBoolVar(f"total_any_{emp.id}_{date_idx}")
                    model.Add(sum(day_shift_vars) >= 1).OnlyEnforceIf(works_any)
                    model.Add(sum(day_shift_vars) == 0).OnlyEnforceIf(works_any.Not())
                    any_shift_indicators.append(works_any)
                else:
                    # No shifts possible on this day
                    zero_var = model.NewBoolVar(f"total_zero_{emp.id}_{date_idx}")
                    model.Add(zero_var == 0)
                    any_shift_indicators.append(zero_var)
            
            # HARD: At most max_total_consecutive working days in any (max+1)-day window
            if len(any_shift_indicators) == max_total_consecutive + 1:
                model.Add(sum(any_shift_indicators) <= max_total_consecutive)
    
    return consecutive_violation_penalties


