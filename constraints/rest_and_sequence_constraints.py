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


def add_rest_time_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    teams: List[Team] = None,
    violation_tracker=None,
    previous_employee_shifts: Dict[Tuple[int, date], str] = None,
):
    """
    SOFT CONSTRAINT: Minimum 11 hours rest between shifts (allows violations for feasibility).
    
    Per @TimUx: Rules should be followed, but exceptions are allowed when necessary to make
    planning feasible. Violations are tracked and reported in the summary.
    
    Forbidden transitions (violate 11-hour rest):
    - S → F (Spät 21:45 → Früh 05:45 = 8 hours)
    - N → F (Nacht 05:45 → Früh 05:45 = 0 hours in same day context)
    - N → S (Nacht 05:45 → Spät 13:45 = 8 hours, below the required 11h)
    
    Implementation:
    - Sunday→Monday transitions: Medium penalty (5000 points - expected with team rotation)
    - Other weekday transitions: Very high penalty (50000 points - strongly discouraged)
    
    NOTE: Penalty weights have been significantly increased (from 50/500 to 5000/50000) to
    prevent rest time violations from being preferred over other soft constraints. This ensures
    that S→F, N→F, and N→S transitions are only accepted when absolutely necessary for feasibility,
    not as a convenience to satisfy lower-priority constraints.
    
    Returns:
        List of penalty variables for rest time violations (to be minimized in objective)
    """
    # Define shift end times (approximate, for determining forbidden transitions)
    shift_end_times = {
        "F": 13.75,  # 13:45
        "S": 21.75,  # 21:45
        "N": 5.75,   # 05:45 (next day)
    }
    
    shift_start_times = {
        "F": 5.75,   # 05:45
        "S": 13.75,  # 13:45
        "N": 21.75,  # 21:45
    }
    
    # Track violation penalties
    rest_violation_penalties = []
    
    # For each employee, track forbidden transitions between consecutive days
    for emp in employees:
        if not emp.team_id:
            continue
        
        for i in range(len(dates) - 1):
            today = dates[i]
            tomorrow = dates[i + 1]
            
            # Get today's shift (either team shift or cross-team)
            today_shifts = []
            today_shift_codes = []
            
            # Check team shift for today
            if today.weekday() < 5 and (emp.id, today) in employee_active:
                # Find team's shift this week
                week_idx = None
                for w_idx, week_dates in enumerate(weeks):
                    if today in week_dates:
                        week_idx = w_idx
                        break
                
                if week_idx is not None:
                    team = None
                    for t in teams:
                        if t.id == emp.team_id:
                            team = t
                            break
                    
                    if team:
                        for shift_code in shift_codes:
                            if (team.id, week_idx, shift_code) in team_shift:
                                # Create variable: emp has this shift today
                                has_shift = model.NewBoolVar(f"emp{emp.id}_has{shift_code}_{today}")
                                model.AddMultiplicationEquality(
                                    has_shift,
                                    [employee_active[(emp.id, today)], team_shift[(team.id, week_idx, shift_code)]]
                                )
                                today_shifts.append(has_shift)
                                today_shift_codes.append(shift_code)
            elif today.weekday() >= 5 and (emp.id, today) in employee_weekend_shift:
                # Weekend team shift
                week_idx = None
                for w_idx, week_dates in enumerate(weeks):
                    if today in week_dates:
                        week_idx = w_idx
                        break
                
                if week_idx is not None:
                    team = None
                    for t in teams:
                        if t.id == emp.team_id:
                            team = t
                            break
                    
                    if team:
                        for shift_code in shift_codes:
                            if (team.id, week_idx, shift_code) in team_shift:
                                # Create variable: emp has this shift today
                                has_shift = model.NewBoolVar(f"emp{emp.id}_has{shift_code}_{today}")
                                model.AddMultiplicationEquality(
                                    has_shift,
                                    [employee_weekend_shift[(emp.id, today)], team_shift[(team.id, week_idx, shift_code)]]
                                )
                                today_shifts.append(has_shift)
                                today_shift_codes.append(shift_code)
            
            # Check cross-team shifts for today
            for shift_code in shift_codes:
                if today.weekday() < 5 and (emp.id, today, shift_code) in employee_cross_team_shift:
                    today_shifts.append(employee_cross_team_shift[(emp.id, today, shift_code)])
                    today_shift_codes.append(shift_code)
                elif today.weekday() >= 5 and (emp.id, today, shift_code) in employee_cross_team_weekend:
                    today_shifts.append(employee_cross_team_weekend[(emp.id, today, shift_code)])
                    today_shift_codes.append(shift_code)
            
            # Get tomorrow's possible shifts (team or cross-team)
            tomorrow_shifts = []
            tomorrow_shift_codes = []
            
            # Similar logic for tomorrow...
            if tomorrow.weekday() < 5 and (emp.id, tomorrow) in employee_active:
                week_idx = None
                for w_idx, week_dates in enumerate(weeks):
                    if tomorrow in week_dates:
                        week_idx = w_idx
                        break
                
                if week_idx is not None:
                    team = None
                    for t in teams:
                        if t.id == emp.team_id:
                            team = t
                            break
                    
                    if team:
                        for shift_code in shift_codes:
                            if (team.id, week_idx, shift_code) in team_shift:
                                has_shift = model.NewBoolVar(f"emp{emp.id}_has{shift_code}_{tomorrow}")
                                model.AddMultiplicationEquality(
                                    has_shift,
                                    [employee_active[(emp.id, tomorrow)], team_shift[(team.id, week_idx, shift_code)]]
                                )
                                tomorrow_shifts.append(has_shift)
                                tomorrow_shift_codes.append(shift_code)
            elif tomorrow.weekday() >= 5 and (emp.id, tomorrow) in employee_weekend_shift:
                week_idx = None
                for w_idx, week_dates in enumerate(weeks):
                    if tomorrow in week_dates:
                        week_idx = w_idx
                        break
                
                if week_idx is not None:
                    team = None
                    for t in teams:
                        if t.id == emp.team_id:
                            team = t
                            break
                    
                    if team:
                        for shift_code in shift_codes:
                            if (team.id, week_idx, shift_code) in team_shift:
                                has_shift = model.NewBoolVar(f"emp{emp.id}_has{shift_code}_{tomorrow}")
                                model.AddMultiplicationEquality(
                                    has_shift,
                                    [employee_weekend_shift[(emp.id, tomorrow)], team_shift[(team.id, week_idx, shift_code)]]
                                )
                                tomorrow_shifts.append(has_shift)
                                tomorrow_shift_codes.append(shift_code)
            
            # Cross-team for tomorrow
            for shift_code in shift_codes:
                if tomorrow.weekday() < 5 and (emp.id, tomorrow, shift_code) in employee_cross_team_shift:
                    tomorrow_shifts.append(employee_cross_team_shift[(emp.id, tomorrow, shift_code)])
                    tomorrow_shift_codes.append(shift_code)
                elif tomorrow.weekday() >= 5 and (emp.id, tomorrow, shift_code) in employee_cross_team_weekend:
                    tomorrow_shifts.append(employee_cross_team_weekend[(emp.id, tomorrow, shift_code)])
                    tomorrow_shift_codes.append(shift_code)
            
            # Track forbidden transitions: S→F, N→F, and N→S (as soft penalties)
            # Per @TimUx: Allow violations when necessary for feasibility, but penalize them
            # Forbidden because rest time would be < 11h:
            #   S→F: Spät ends 21:45, Früh starts 05:45 next day → 8h rest
            #   N→F: Nacht ends 05:45 next day, Früh starts 05:45 → 0h rest
            #   N→S: Nacht ends 05:45 next day, Spät starts 13:45 → 8h rest
            for i_today, today_shift_code in enumerate(today_shift_codes):
                for i_tomorrow, tomorrow_shift_code in enumerate(tomorrow_shift_codes):
                    # Check if this is a forbidden transition
                    if (today_shift_code == "S" and tomorrow_shift_code == "F") or \
                       (today_shift_code == "N" and tomorrow_shift_code == "F") or \
                       (today_shift_code == "N" and tomorrow_shift_code == "S"):
                        
                        # Create a violation indicator variable
                        # violation = 1 if both shifts happen (forbidden transition occurs)
                        violation = model.NewBoolVar(f"rest_violation_{emp.id}_{today}_{tomorrow}_{today_shift_code}{tomorrow_shift_code}")
                        
                        # violation = 1 if BOTH today_shift AND tomorrow_shift are active
                        # This is: violation >= today_shift + tomorrow_shift - 1
                        model.Add(violation >= today_shifts[i_today] + tomorrow_shifts[i_tomorrow] - 1)
                        model.Add(violation <= today_shifts[i_today])
                        model.Add(violation <= tomorrow_shifts[i_tomorrow])
                        
                        # Check if this is Sunday→Monday (expected with team rotation)
                        is_sunday_monday = (today.weekday() == 6 and tomorrow.weekday() == 0)
                        
                        if is_sunday_monday:
                            # Lower penalty for Sunday→Monday violations (expected with team rotation)
                            # Weight: 5000 points per violation (still discouraged but allowed when necessary)
                            penalty_weight = 5000
                        else:
                            # Very high penalty for other violations (should be strongly avoided)
                            # Weight: 50000 points per violation (much higher than other constraints)
                            # This ensures rest time violations are only accepted when absolutely necessary
                            penalty_weight = 50000
                        
                        # Add weighted penalty to objective using proper multiplication
                        penalty_var = model.NewIntVar(0, penalty_weight, f"rest_penalty_{emp.id}_{today}_{tomorrow}_{today_shift_code}{tomorrow_shift_code}")
                        model.AddMultiplicationEquality(penalty_var, [violation, penalty_weight])
                        rest_violation_penalties.append(penalty_var)

    # Handle month-boundary: enforce rest-time between the last known shift of the
    # previous planning period and the first day of the current planning period.
    # previous_employee_shifts maps (emp_id, date) -> shift_code for dates BEFORE dates[0].
    if previous_employee_shifts and dates:
        first_day = dates[0]
        prev_day = first_day - timedelta(days=1)
        for emp in employees:
            if not emp.team_id:
                continue
            prev_shift_code = previous_employee_shifts.get((emp.id, prev_day))
            # S and N can cause forbidden transitions into F or S the next day:
            #   S→F, N→F: already handled above
            #   N→S: Nacht ends 05:45, Spät starts 13:45 → 8h rest < 11h
            if prev_shift_code not in ("S", "N"):
                continue

            # Collect CP-SAT indicator vars for each possible shift on the first day
            first_day_shifts = []
            first_day_shift_codes = []

            if first_day.weekday() < 5 and (emp.id, first_day) in employee_active:
                week_idx = next(
                    (w for w, wd in enumerate(weeks) if first_day in wd), None
                )
                if week_idx is not None:
                    team = next(
                        (t for t in (teams or []) if t.id == emp.team_id), None
                    )
                    if team:
                        for sc in shift_codes:
                            if (team.id, week_idx, sc) in team_shift:
                                bv = model.NewBoolVar(
                                    f"bnd_{emp.id}_{sc}_{first_day}_wd"
                                )
                                model.AddMultiplicationEquality(
                                    bv,
                                    [
                                        employee_active[(emp.id, first_day)],
                                        team_shift[(team.id, week_idx, sc)],
                                    ],
                                )
                                first_day_shifts.append(bv)
                                first_day_shift_codes.append(sc)
            elif first_day.weekday() >= 5 and (emp.id, first_day) in employee_weekend_shift:
                week_idx = next(
                    (w for w, wd in enumerate(weeks) if first_day in wd), None
                )
                if week_idx is not None:
                    team = next(
                        (t for t in (teams or []) if t.id == emp.team_id), None
                    )
                    if team:
                        for sc in shift_codes:
                            if (team.id, week_idx, sc) in team_shift:
                                bv = model.NewBoolVar(
                                    f"bnd_{emp.id}_{sc}_{first_day}_we"
                                )
                                model.AddMultiplicationEquality(
                                    bv,
                                    [
                                        employee_weekend_shift[(emp.id, first_day)],
                                        team_shift[(team.id, week_idx, sc)],
                                    ],
                                )
                                first_day_shifts.append(bv)
                                first_day_shift_codes.append(sc)

            # Cross-team shifts on first day
            for sc in shift_codes:
                if (
                    first_day.weekday() < 5
                    and (emp.id, first_day, sc) in employee_cross_team_shift
                ):
                    first_day_shifts.append(employee_cross_team_shift[(emp.id, first_day, sc)])
                    first_day_shift_codes.append(sc)
                elif (
                    first_day.weekday() >= 5
                    and (emp.id, first_day, sc) in employee_cross_team_weekend
                ):
                    first_day_shifts.append(employee_cross_team_weekend[(emp.id, first_day, sc)])
                    first_day_shift_codes.append(sc)

            # Apply penalty for each forbidden transition from previous day:
            #   S→F, N→F (insufficient rest), N→S (only 8h rest)
            # Since prev_shift_code is a known constant, violation = first_day_has_target_shift variable
            _SUNDAY = 6
            _MONDAY = 0
            for i_fd, fd_sc in enumerate(first_day_shift_codes):
                is_forbidden = (
                    (prev_shift_code == "S" and fd_sc == "F") or
                    (prev_shift_code == "N" and fd_sc == "F") or
                    (prev_shift_code == "N" and fd_sc == "S")
                )
                if is_forbidden:
                    is_sunday_monday = (
                        prev_day.weekday() == _SUNDAY and first_day.weekday() == _MONDAY
                    )
                    penalty_weight = 5000 if is_sunday_monday else 50000
                    violation = first_day_shifts[i_fd]
                    penalty_var = model.NewIntVar(
                        0, penalty_weight, f"bnd_penalty_{emp.id}_{first_day}"
                    )
                    model.AddMultiplicationEquality(penalty_var, [violation, penalty_weight])
                    rest_violation_penalties.append(penalty_var)

    return rest_violation_penalties


def add_shift_stability_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    teams: List[Team] = None
):
    """
    SOFT CONSTRAINT: Prevent shift hopping (rapid changes like N→S→N).
    
    Requirement from issue #2:
    - Prevent daily switching between shift types (e.g., night-late-night)
    - Prefer gradual transitions (e.g., night-night-late) 
    - If changes must happen, they should be stable (e.g., N→N→S rather than N→S→N)
    
    Implementation:
    - Penalize "zig-zag" shift patterns over 3 consecutive days
    - Pattern A→B→A gets high penalty (200 points)
    - Pattern A→A→B gets low/no penalty (stable, then gradual change)
    - Helps create stable, predictable schedules
    
    Returns:
        List of penalty variables for shift hopping violations
    """
    hopping_penalties = []
    
    # Define shift change penalty
    # Higher penalty for rapid back-and-forth changes
    HOPPING_PENALTY = 200
    
    # Helper to collect shift assignment for a day
    def get_shift_vars_for_day(emp_id, d):
        """Returns list of (shift_code, var) tuples for this day"""
        result = []
        weekday = d.weekday()
        
        # Team shift (weekday)
        if weekday < 5 and (emp_id, d) in employee_active:
            # Find team and week
            week_idx = None
            for w_idx, week_dates in enumerate(weeks):
                if d in week_dates:
                    week_idx = w_idx
                    break
            
            if week_idx is not None:
                team = None
                for t in teams:
                    if t.id == emp_id or any(e.id == emp_id for e in employees if e.team_id == t.id):
                        for emp in employees:
                            if emp.id == emp_id and emp.team_id == t.id:
                                team = t
                                break
                        break
                
                if team:
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            # This shift is active if both team has it AND employee is active
                            result.append((shift_code, [team_shift[(team.id, week_idx, shift_code)], 
                                                        employee_active[(emp_id, d)]]))
        
        # Team shift (weekend)
        elif weekday >= 5 and (emp_id, d) in employee_weekend_shift:
            # Find team and week
            week_idx = None
            for w_idx, week_dates in enumerate(weeks):
                if d in week_dates:
                    week_idx = w_idx
                    break
            
            if week_idx is not None:
                team = None
                for emp in employees:
                    if emp.id == emp_id:
                        for t in teams:
                            if t.id == emp.team_id:
                                team = t
                                break
                        break
                
                if team:
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            # This shift is active if both team has it AND employee works weekend
                            result.append((shift_code, [team_shift[(team.id, week_idx, shift_code)],
                                                        employee_weekend_shift[(emp_id, d)]]))
        
        # Cross-team shifts (weekday)
        if weekday < 5:
            for shift_code in shift_codes:
                if (emp_id, d, shift_code) in employee_cross_team_shift:
                    result.append((shift_code, [employee_cross_team_shift[(emp_id, d, shift_code)]]))
        
        # Cross-team shifts (weekend)
        elif weekday >= 5:
            for shift_code in shift_codes:
                if (emp_id, d, shift_code) in employee_cross_team_weekend:
                    result.append((shift_code, [employee_cross_team_weekend[(emp_id, d, shift_code)]]))
        
        return result
    
    for emp in employees:
        if not emp.team_id:
            continue
        
        # Check triplets of consecutive working days
        for i in range(len(dates) - 2):
            day1 = dates[i]
            day2 = dates[i + 1]
            day3 = dates[i + 2]
            
            # Get possible shifts for all three days
            shifts1 = get_shift_vars_for_day(emp.id, day1)
            shifts2 = get_shift_vars_for_day(emp.id, day2)
            shifts3 = get_shift_vars_for_day(emp.id, day3)
            
            # Check for hopping patterns: shift1 != shift2 AND shift2 != shift3 AND shift1 == shift3
            # This indicates A→B→A pattern
            for code1, vars1 in shifts1:
                for code2, vars2 in shifts2:
                    for code3, vars3 in shifts3:
                        # Only penalize if we have a "zig-zag": A→B→A
                        if code1 != code2 and code2 != code3 and code1 == code3:
                            # This is a hopping pattern!
                            # Create penalty variable: penalty is active if all three shifts are active
                            # We need all vars to be 1: day1 has code1, day2 has code2, day3 has code3
                            
                            # Collect all variables that must be 1
                            all_active = []
                            for v in vars1:
                                all_active.append(v)
                            for v in vars2:
                                all_active.append(v)
                            for v in vars3:
                                all_active.append(v)
                            
                            # Create boolean: is_hopping = (all variables are 1)
                            is_hopping = model.NewBoolVar(f"hop_{emp.id}_{i}")
                            # Use proper constraint form for OR-Tools
                            # is_hopping = 1 if all variables are 1
                            # This is an AND operation: is_hopping = AND(all_active)
                            model.AddBoolAnd(all_active).OnlyEnforceIf(is_hopping)
                            model.AddBoolOr([v.Not() for v in all_active]).OnlyEnforceIf(is_hopping.Not())
                            
                            # Add penalty
                            penalty_var = model.NewIntVar(0, HOPPING_PENALTY, f"hop_pen_{emp.id}_{i}")
                            model.AddMultiplicationEquality(penalty_var, [is_hopping, HOPPING_PENALTY])
                            hopping_penalties.append(penalty_var)
    
    return hopping_penalties


def add_shift_sequence_grouping_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    teams: List[Team] = None
):
    """
    SOFT CONSTRAINT: Prevent isolated shift types in sequences of working days.

    Requirements:
    - When an employee works multiple shift types in a period, they should be grouped
    - No single days or small groups of one shift type isolated between days of another shift type
    - Examples (where "-" represents free day):
      * INVALID: S S - F S S (working days: S S F S S - F isolated in middle)
      * INVALID: S - F S S S S (working days: S F S S S S - F isolated at beginning)
      * VALID: F F F S S S (shifts properly grouped)
      * VALID: S S S - - F F F (shifts properly grouped, free days don't matter)

    Implementation (O(n * WINDOW) per employee):
    - Use a sliding window of WINDOW calendar days.
    - For each potential "middle" day (shift_B), look backwards and forwards within
      WINDOW days for days with a different shift (shift_A) to detect A-B-A patterns.
    - This replaces the previous O(n³) global check with an O(n) scan.

    Returns:
        List of penalty variables for shift sequence grouping violations
    """
    grouping_penalties = []

    # Penalty weights – kept high so the solver strongly avoids isolated shifts,
    # but split into two tiers:
    #   close-range (≤7 days apart): ULTRA_HIGH_PENALTY – almost forbidden
    #   medium-range (8-14 days apart): ISOLATION_PENALTY – strongly discouraged
    ISOLATION_PENALTY = 100_000
    ULTRA_HIGH_PENALTY = 200_000
    WINDOW_CLOSE = 7    # calendar-day radius for ultra-high penalty
    WINDOW_FAR = 14     # calendar-day radius for normal isolation penalty

    # Pre-compute employee→team and date→week-index lookups once
    emp_to_team: Dict[int, "Team"] = {}
    if teams:
        for emp in employees:
            if emp.team_id:
                for t in teams:
                    if t.id == emp.team_id:
                        emp_to_team[emp.id] = t
                        break

    date_to_week: Dict[date, int] = {}
    for w_idx, week_dates in enumerate(weeks):
        for d in week_dates:
            date_to_week[d] = w_idx

    def get_shift_type_for_day(emp_id: int, d: date) -> Dict[str, List]:
        """
        Returns {shift_code: [list_of_cp_sat_vars]} for the given employee and date.
        The shift is "active" iff all variables in the list are 1.
        """
        result: Dict[str, List] = {}
        weekday = d.weekday()
        week_idx = date_to_week.get(d)
        if week_idx is None:
            return result

        team = emp_to_team.get(emp_id)

        # Team shift on a weekday
        if weekday < 5 and (emp_id, d) in employee_active:
            if team:
                for sc in shift_codes:
                    if (team.id, week_idx, sc) in team_shift:
                        if sc not in result:
                            result[sc] = []
                        result[sc].extend([
                            team_shift[(team.id, week_idx, sc)],
                            employee_active[(emp_id, d)],
                        ])

        # Team shift on a weekend
        elif weekday >= 5 and (emp_id, d) in employee_weekend_shift:
            if team:
                for sc in shift_codes:
                    if (team.id, week_idx, sc) in team_shift:
                        if sc not in result:
                            result[sc] = []
                        result[sc].extend([
                            team_shift[(team.id, week_idx, sc)],
                            employee_weekend_shift[(emp_id, d)],
                        ])

        # Cross-team shifts (weekday)
        if weekday < 5:
            for sc in shift_codes:
                if (emp_id, d, sc) in employee_cross_team_shift:
                    if sc not in result:
                        result[sc] = []
                    result[sc].append(employee_cross_team_shift[(emp_id, d, sc)])

        # Cross-team shifts (weekend)
        if weekday >= 5:
            for sc in shift_codes:
                if (emp_id, d, sc) in employee_cross_team_weekend:
                    if sc not in result:
                        result[sc] = []
                    result[sc].append(employee_cross_team_weekend[(emp_id, d, sc)])

        return result

    for emp in employees:
        if not emp.team_id:
            continue

        # Build sorted list of (date, shift_data) for all potential working days
        period_shift_data = []
        for d in dates:
            shift_data = get_shift_type_for_day(emp.id, d)
            if shift_data:
                period_shift_data.append((d, shift_data))

        n = len(period_shift_data)
        if n < 3:
            continue

        # Sliding-window A-B-A detection:
        # For each "middle" day (day_mid with shift_B), scan a window of WINDOW_FAR
        # calendar days before AND after for an "outer" day with a different shift_A.
        # This is O(n * WINDOW) instead of O(n³).
        for mid_idx in range(n):
            day_mid, shifts_mid = period_shift_data[mid_idx]

            for shift_B in shift_codes:
                if shift_B not in shifts_mid:
                    continue

                for shift_A in shift_codes:
                    if shift_A == shift_B:
                        continue

                    # Collect candidate "before" days with shift_A within WINDOW_FAR
                    before_candidates = []
                    for before_idx in range(mid_idx - 1, -1, -1):
                        day_before, shifts_before = period_shift_data[before_idx]
                        gap = (day_mid - day_before).days
                        if gap > WINDOW_FAR:
                            break
                        if shift_A in shifts_before:
                            before_candidates.append((day_before, shifts_before, gap))

                    if not before_candidates:
                        continue

                    # Collect candidate "after" days with shift_A within WINDOW_FAR
                    after_candidates = []
                    for after_idx in range(mid_idx + 1, n):
                        day_after, shifts_after = period_shift_data[after_idx]
                        gap = (day_after - day_mid).days
                        if gap > WINDOW_FAR:
                            break
                        if shift_A in shifts_after:
                            after_candidates.append((day_after, shifts_after, gap))

                    if not after_candidates:
                        continue

                    # For every (before, after) pair create one violation variable.
                    # Use the penalty tier based on the total span of the pattern.
                    for day_before, shifts_before, gap_before in before_candidates:
                        for day_after, shifts_after, gap_after in after_candidates:
                            total_span = (day_after - day_before).days
                            penalty_weight = (
                                ULTRA_HIGH_PENALTY if total_span <= WINDOW_CLOSE
                                else ISOLATION_PENALTY
                            )

                            all_active = (
                                list(shifts_before[shift_A])
                                + list(shifts_mid[shift_B])
                                + list(shifts_after[shift_A])
                            )

                            vname = (
                                f"sg_{emp.id}_{day_before.isoformat()}"
                                f"_{day_mid.isoformat()}_{day_after.isoformat()}"
                                f"_{shift_A}{shift_B}"
                            )
                            violation_var = model.NewBoolVar(vname)
                            model.AddBoolAnd(all_active).OnlyEnforceIf(violation_var)
                            model.AddBoolOr(
                                [v.Not() for v in all_active]
                            ).OnlyEnforceIf(violation_var.Not())

                            penalty_var = model.NewIntVar(
                                0, penalty_weight,
                                f"sg_pen_{emp.id}_{day_before.isoformat()}"
                                f"_{day_mid.isoformat()}_{day_after.isoformat()}"
                                f"_{shift_A}{shift_B}"
                            )
                            model.Add(penalty_var == violation_var * penalty_weight)
                            grouping_penalties.append(penalty_var)
    
    return grouping_penalties


def add_minimum_consecutive_weekday_shifts_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    teams: List[Team] = None
):
    """
    SOFT CONSTRAINT: Enforce minimum 2 consecutive days for same shift type during weekdays.
    
    Requirements (from problem statement):
    - During weekdays (Mon-Fri), employees must work at least 2 consecutive days 
      with the same shift type
    - Having a single day with one shift type surrounded by other shifts or free days is not allowed
    - Weekends (Sat-Sun) can have single-day shifts (exceptions allowed)
    - This prevents patterns like:
      * F on one day, N on next day, S on third day (3 different shifts in 3 days)
      * N-N-F-N-N (single F isolated between N shifts)
      * S-S-N-S-S (single N isolated between S shifts)
    
    Implementation:
    - For each pair of consecutive weekdays where an employee works:
      * If they work different shift types on consecutive days, apply penalty
      * This enforces that shift types must be grouped into blocks of at least 2 days
    - Also detect single isolated days (X-Y-X pattern) for stronger enforcement
    - Weekend days (Sat-Sun) are excluded from this check
    
    Returns:
        List of penalty variables for minimum consecutive days violations
    """
    min_consecutive_penalties = []
    
    # Very high penalty for shift type changes on consecutive weekdays
    # Increased dramatically to make this the top priority constraint
    SHIFT_CHANGE_PENALTY = 6000  # Extremely high penalty to enforce minimum 2 consecutive days
    # Even higher penalty for single isolated days
    # Increased even further to prevent A-B-A patterns at all costs
    SINGLE_DAY_PENALTY = 8000  # Maximum priority penalty for clear violations
    
    # Pre-compute date-to-week mapping
    date_to_week = {}
    for week_idx, week_dates in enumerate(weeks):
        for d in week_dates:
            date_to_week[d] = week_idx
    
    # Pre-compute employee-to-team mapping
    emp_to_team = {}
    if teams:
        for emp in employees:
            if emp.team_id:
                for team in teams:
                    if team.id == emp.team_id:
                        emp_to_team[emp.id] = team
                        break
    
    # Helper function to get shift type variables for a specific day
    def get_shift_vars_for_day(emp_id, d):
        """Returns dict of shift_code -> list of constraint variables"""
        result = {}
        weekday = d.weekday()
        week_idx = date_to_week.get(d)
        
        if week_idx is None:
            return result
        
        # Team shift (weekday)
        if weekday < 5 and (emp_id, d) in employee_active:
            team = emp_to_team.get(emp_id)
            if team:
                for shift_code in shift_codes:
                    if (team.id, week_idx, shift_code) in team_shift:
                        if shift_code not in result:
                            result[shift_code] = []
                        result[shift_code].extend([
                            team_shift[(team.id, week_idx, shift_code)],
                            employee_active[(emp_id, d)]
                        ])
        
        # Team shift (weekend)
        elif weekday >= 5 and (emp_id, d) in employee_weekend_shift:
            team = emp_to_team.get(emp_id)
            if team:
                for shift_code in shift_codes:
                    if (team.id, week_idx, shift_code) in team_shift:
                        if shift_code not in result:
                            result[shift_code] = []
                        result[shift_code].extend([
                            team_shift[(team.id, week_idx, shift_code)],
                            employee_weekend_shift[(emp_id, d)]
                        ])
        
        # Cross-team shifts (weekday)
        if weekday < 5:
            for shift_code in shift_codes:
                if (emp_id, d, shift_code) in employee_cross_team_shift:
                    if shift_code not in result:
                        result[shift_code] = []
                    result[shift_code].append(employee_cross_team_shift[(emp_id, d, shift_code)])
        
        # Cross-team shifts (weekend)
        elif weekday >= 5:
            for shift_code in shift_codes:
                if (emp_id, d, shift_code) in employee_cross_team_weekend:
                    if shift_code not in result:
                        result[shift_code] = []
                    result[shift_code].append(employee_cross_team_weekend[(emp_id, d, shift_code)])
        
        return result
    
    # Helper function to get working weekdays for an employee
    def get_working_weekdays(emp_id, dates_list):
        """
        Returns list of (date, shifts_dict) tuples for working weekdays only.
        Filters out weekends and days where employee has no potential shifts.
        """
        working_weekdays = []
        for d in dates_list:
            # Only weekdays (Mon-Fri)
            if d.weekday() >= 5:
                continue
            shifts = get_shift_vars_for_day(emp_id, d)
            # Only days where employee could work (has potential shift assignments)
            if shifts:
                working_weekdays.append((d, shifts))
        return working_weekdays
    
    # Check each employee's schedule
    for emp in employees:
        if not emp.team_id:
            continue
        
        # Build list of potential working weekdays once for efficiency
        working_weekdays_with_shifts = get_working_weekdays(emp.id, dates)
        
        # PART 1: Check for shift type changes on consecutive WORKING weekdays
        # If employee works on two consecutive WORKING weekdays, they should work the same shift
        # KEY FIX: Check consecutive CALENDAR days, not just consecutive list positions
        
        # Check consecutive WORKING days (must be calendar-consecutive weekdays)
        for i in range(len(working_weekdays_with_shifts) - 1):
            day1, shifts1 = working_weekdays_with_shifts[i]
            day2, shifts2 = working_weekdays_with_shifts[i + 1]
            
            # CRITICAL FIX: Only check if days are actually consecutive calendar days
            # Skip if there's a gap (e.g., Monday -> Wednesday with Tuesday off)
            calendar_day_diff = (day2 - day1).days
            if calendar_day_diff != 1:
                continue
            
            # Check if employee works different shift types on these consecutive working days
            for shift_A in shift_codes:
                for shift_B in shift_codes:
                    if shift_A == shift_B:
                        continue
                    
                    # Check if this pattern is possible
                    if shift_A not in shifts1 or shift_B not in shifts2:
                        continue
                    
                    # Create violation: employee works shift_A on day1 AND shift_B on day2
                    all_vars = []
                    all_vars.extend(shifts1[shift_A])
                    all_vars.extend(shifts2[shift_B])
                    
                    # Create violation indicator
                    violation_var = model.NewBoolVar(
                        f"consec_change_{emp.id}_{day1.isoformat()}_{day2.isoformat()}_{shift_A}_{shift_B}"
                    )
                    model.AddBoolAnd(all_vars).OnlyEnforceIf(violation_var)
                    model.AddBoolOr([v.Not() for v in all_vars]).OnlyEnforceIf(violation_var.Not())
                    
                    # Add penalty
                    penalty_var = model.NewIntVar(
                        0, SHIFT_CHANGE_PENALTY,
                        f"consec_change_pen_{emp.id}_{day1.isoformat()}_{day2.isoformat()}_{shift_A}_{shift_B}"
                    )
                    model.Add(penalty_var == violation_var * SHIFT_CHANGE_PENALTY)
                    min_consecutive_penalties.append(penalty_var)
        
        # PART 2: Check for single isolated days or blocks among WORKING DAYS (stronger penalty)
        # Pattern: shift_A on working_day1, shift_B on working_day2, shift_A on working_day3 
        # (working_day2 is isolated) - CRITICAL FIX: Check calendar-consecutive working days
        
        # This catches patterns like N-S-N where S is isolated, considering calendar days
        # We need to check actual calendar-consecutive working days, not just list positions
        
        # Check 3-day windows among working days, but only if they're within a reasonable calendar range
        for i in range(len(working_weekdays_with_shifts) - 2):
            day1, shifts1 = working_weekdays_with_shifts[i]
            day2, shifts2 = working_weekdays_with_shifts[i + 1]
            day3, shifts3 = working_weekdays_with_shifts[i + 2]
            
            # Only check if all three days are within the same week (7-day window)
            # This prevents checking patterns across weekly boundaries
            day_span = (day3 - day1).days
            if day_span >= 7:
                continue
            
            # Check for pattern: shift_A on day1, shift_B on day2, shift_A on day3
            # This is the A-B-A pattern where shift_B is sandwiched between two occurrences of shift_A
            # Shift_B is isolated (appears only on a single day between other shifts)
            for shift_A in shift_codes:
                for shift_B in shift_codes:
                    if shift_A == shift_B:
                        continue
                    
                    # Check if this pattern is possible
                    if shift_A not in shifts1 or shift_B not in shifts2 or shift_A not in shifts3:
                        continue
                    
                    # Create violation: all three conditions must be true
                    # 1. Employee works shift_A on day1
                    # 2. Employee works shift_B on day2
                    # 3. Employee works shift_A on day3
                    all_vars = []
                    all_vars.extend(shifts1[shift_A])
                    all_vars.extend(shifts2[shift_B])
                    all_vars.extend(shifts3[shift_A])
                    
                    # Create violation indicator
                    violation_var = model.NewBoolVar(
                        f"min_consec_{emp.id}_{day1.isoformat()}_{day2.isoformat()}_{day3.isoformat()}_{shift_A}_{shift_B}"
                    )
                    model.AddBoolAnd(all_vars).OnlyEnforceIf(violation_var)
                    model.AddBoolOr([v.Not() for v in all_vars]).OnlyEnforceIf(violation_var.Not())
                    
                    # Add penalty
                    penalty_var = model.NewIntVar(
                        0, SINGLE_DAY_PENALTY,
                        f"min_consec_pen_{emp.id}_{day1.isoformat()}_{day2.isoformat()}_{day3.isoformat()}_{shift_A}_{shift_B}"
                    )
                    model.Add(penalty_var == violation_var * SINGLE_DAY_PENALTY)
                    min_consecutive_penalties.append(penalty_var)
    
    return min_consecutive_penalties


