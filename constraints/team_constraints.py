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


def add_team_shift_assignment_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType] = None
):
    """
    HARD CONSTRAINT: Each team must have exactly ONE shift per week.
    
    Constraint: For each team and week:
        Sum(team_shift[team][week][shift] for all ALLOWED shifts) == 1
    
    IMPORTANT: Only allows shifts that are configured in TeamShiftAssignments.
    If a team has allowed_shift_type_ids configured, only those shifts are allowed.
    If a team has no configuration (empty list), it can work all shifts (backward compatibility).
    
    EXCLUDES virtual team "Fire Alarm System" (ID 99) which doesn't participate in rotation.
    """
    # Build shift type ID to code mapping
    shift_id_to_code = {}
    if shift_types:
        for st in shift_types:
            shift_id_to_code[st.id] = st.code
    
    for team in teams:
        for week_idx in range(len(weeks)):
            shift_vars = []
            for shift_code in shift_codes:
                if (team.id, week_idx, shift_code) not in team_shift:
                    continue
                
                # Check if this team is allowed to work this shift
                # If team has allowed_shift_type_ids configured, enforce it
                if team.allowed_shift_type_ids:
                    # Find shift type ID for this code
                    shift_type_id = None
                    for st_id, st_code in shift_id_to_code.items():
                        if st_code == shift_code:
                            shift_type_id = st_id
                            break
                    
                    # Only add this shift if team is allowed to work it
                    if shift_type_id and shift_type_id in team.allowed_shift_type_ids:
                        shift_vars.append(team_shift[(team.id, week_idx, shift_code)])
                    else:
                        # Team is NOT allowed to work this shift - force it to 0
                        model.Add(team_shift[(team.id, week_idx, shift_code)] == 0)
                else:
                    # No configuration - allow all shifts (backward compatibility)
                    shift_vars.append(team_shift[(team.id, week_idx, shift_code)])
            
            # Team must have exactly one shift per week (from allowed shifts only)
            if shift_vars:
                model.Add(sum(shift_vars) == 1)
            # If no shift vars (team has no allowed shifts), this is an error in configuration
            # but we don't fail - the team simply won't be assigned any shifts


def add_team_rotation_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    shift_types: List[ShiftType] = None,
    rotation_patterns: Dict[int, List[str]] = None
):
    """
    HARD CONSTRAINT: Teams follow rotation pattern (database-driven or default F → N → S).
    
    Each team follows a rotation cycle with offset based on team ID.
    
    If rotation_patterns is provided and a team has a rotation_group_id, 
    uses the team-specific pattern from the database.
    Otherwise, falls back to the default hardcoded pattern: F → N → S.
    
    Example with F → N → S pattern:
        Week 0: Team 1=F, Team 2=N, Team 3=S
        Week 1: Team 1=N, Team 2=S, Team 3=F
        Week 2: Team 1=S, Team 2=F, Team 3=N
        Week 3: Team 1=F, Team 2=N, Team 3=S (repeats)
    
    Manual overrides (locked assignments) take precedence over rotation.
    
    IMPORTANT: Only applies to teams that have the rotation shifts in their allowed shifts.
    Teams with other shift configurations (e.g., only TD/BMT/BSB) are skipped.
    
    Args:
        model: CP-SAT model
        team_shift: Decision variables for team shifts
        teams: List of teams
        weeks: List of weeks (each week is a list of dates)
        shift_codes: List of shift codes
        locked_team_shift: Dict of locked team shifts
        shift_types: List of shift types
        rotation_patterns: Dict mapping rotation_group_id to list of shift codes (from database)
    """
    # Default fallback pattern if no database pattern available
    DEFAULT_ROTATION = ["F", "N", "S"]
    
    locked_team_shift = locked_team_shift or {}
    rotation_patterns = rotation_patterns or {}
    
    # Build shift type ID to code mapping
    shift_id_to_code = {}
    if shift_types:
        for st in shift_types:
            shift_id_to_code[st.id] = st.code
    
    # For each team, assign shifts based on rotation pattern
    sorted_teams = sorted(teams, key=lambda t: t.id)
    
    for team_idx, team in enumerate(sorted_teams):
        # Get rotation pattern for this team
        # Priority: 1) Database pattern for team's rotation group, 2) Default hardcoded pattern
        rotation = DEFAULT_ROTATION  # Start with default
        
        if team.rotation_group_id and team.rotation_group_id in rotation_patterns:
            # Team has a rotation group assigned and it's in the database
            rotation = rotation_patterns[team.rotation_group_id]
        
        # Verify all shifts in rotation are available
        missing_shifts = [s for s in rotation if s not in shift_codes]
        if missing_shifts:
            print(f"[!] Warning: Team '{team.name}' rotation pattern {rotation} contains unavailable shifts: {missing_shifts}. Skipping rotation constraint for this team.")
            continue
        
        # Check if team has all rotation shifts in allowed shifts (if configured)
        if team.allowed_shift_type_ids and shift_id_to_code:
            # Build set of allowed shift codes for this team
            allowed_shift_codes = set()
            for st_id in team.allowed_shift_type_ids:
                if st_id in shift_id_to_code:
                    allowed_shift_codes.add(shift_id_to_code[st_id])
            
            # Check if all rotation shifts are allowed
            rotation_set = set(rotation)
            if not rotation_set.issubset(allowed_shift_codes):
                # Team doesn't have all rotation shifts - skip rotation constraint
                # Team will be constrained by add_team_shift_assignment_constraints instead
                continue
        
        # Team participates in rotation
        for week_idx in range(len(weeks)):
            # Check if this assignment is locked (manual override)
            if (team.id, week_idx) in locked_team_shift:
                # Skip - locked assignment will be applied by _apply_locked_assignments()
                continue
            
            # Calculate which shift this team should have this week
            # CRITICAL FIX: Use ISO week number for consistent rotation across month boundaries
            # This ensures the same calendar week always gets the same shift assignment
            # regardless of which month's planning period it appears in
            week_dates = weeks[week_idx]
            sunday_of_week = week_dates[0]  # First day of week (Sunday)
            iso_year, iso_week, iso_weekday = sunday_of_week.isocalendar()
            
            # Use ISO week number for rotation calculation (absolute reference)
            # This ensures cross-month continuity: if a week spans two months,
            # both planning periods will assign the same shift to the same team
            rotation_idx = (iso_week + team_idx) % len(rotation)
            assigned_shift = rotation[rotation_idx]
            
            # Force this team to have this specific shift this week
            if (team.id, week_idx, assigned_shift) in team_shift:
                model.Add(team_shift[(team.id, week_idx, assigned_shift)] == 1)


def add_employee_weekly_rotation_order_constraints(
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
    SOFT CONSTRAINT: Enforce F → N → S rotation order for employees across weeks.
    
    The rotation order F → N → S means:
    - F can only be followed by N (or repeat F)
    - N can only be followed by S (or repeat N)
    - S can only be followed by F (or repeat S, wrapping around)
    
    Invalid transitions that violate the order:
    - F → S (skips N)
    - N → F (skips S)
    - S → N (skips F)
    
    This constraint applies to both regular team shifts and cross-team assignments.
    According to requirements: "Bevor dieser Rhythmus unterbrochen wird, soll ein 
    Mitarbeiter lieber 2-3 mal die gleiche Schicht machen um wieder in den normalen 
    Rhythmus zu kommen" - employees should rather repeat the same shift 2-3 times 
    than break the rotation order.
    
    Implementation:
    - For each employee, track which shift type they work each week
    - Check week-to-week transitions and penalize invalid ones
    - Very high penalty (10000) to strongly discourage violations
    
    Returns:
        List of penalty variables for rotation order violations
    """
    rotation_order_penalties = []
    
    # Very high penalty to strongly discourage rotation order violations
    ROTATION_ORDER_VIOLATION_PENALTY = 10000
    
    # Define valid transitions in the F → N → S order
    # Each shift can transition to the next in sequence or stay the same
    VALID_NEXT_SHIFTS = {
        "F": ["F", "N"],  # F can go to N or stay F
        "N": ["N", "S"],  # N can go to S or stay N
        "S": ["S", "F"],  # S can go to F (wrap) or stay S
    }
    
    # Only check standard rotation shifts
    rotation_shifts = ["F", "N", "S"]
    if not all(shift in shift_codes for shift in rotation_shifts):
        return rotation_order_penalties  # Cannot enforce if shifts are missing
    
    # For each employee, determine which shift they work each week
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
        
        # Track employee's shift type for each week
        # We need to determine if employee works F, N, or S each week
        # This includes both their team's shift and any cross-team assignments
        for week_idx in range(len(weeks) - 1):  # Check transitions between consecutive weeks
            current_week = weeks[week_idx]
            next_week = weeks[week_idx + 1]
            
            # Determine which shift types the employee works in current week
            current_week_shifts = {}
            for shift_code in rotation_shifts:
                # Check if employee works this shift type during current week
                works_shift_days = []
                
                for d in current_week:
                    weekday = d.weekday()
                    
                    # Regular team shift (weekday)
                    if weekday < 5 and (emp.id, d) in employee_active:
                        if (team.id, week_idx, shift_code) in team_shift:
                            # Employee works if team has shift AND employee is active
                            works_shift_days.append(
                                model.NewBoolVar(f"emp{emp.id}_w{week_idx}_d{d.day}_{shift_code}_regular")
                            )
                            model.AddMultiplicationEquality(
                                works_shift_days[-1],
                                [team_shift[(team.id, week_idx, shift_code)], employee_active[(emp.id, d)]]
                            )
                    
                    # Regular team shift (weekend)
                    elif weekday >= 5 and (emp.id, d) in employee_weekend_shift:
                        if (team.id, week_idx, shift_code) in team_shift:
                            works_shift_days.append(
                                model.NewBoolVar(f"emp{emp.id}_w{week_idx}_d{d.day}_{shift_code}_weekend")
                            )
                            model.AddMultiplicationEquality(
                                works_shift_days[-1],
                                [team_shift[(team.id, week_idx, shift_code)], employee_weekend_shift[(emp.id, d)]]
                            )
                    
                    # Cross-team shift (weekday)
                    if weekday < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        works_shift_days.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    
                    # Cross-team shift (weekend)
                    elif weekday >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        works_shift_days.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                # Create indicator: employee works this shift type at least once this week
                if works_shift_days:
                    shift_indicator = model.NewBoolVar(f"emp{emp.id}_week{week_idx}_{shift_code}_indicator")
                    # shift_indicator = 1 if sum(works_shift_days) > 0
                    model.Add(sum(works_shift_days) >= 1).OnlyEnforceIf(shift_indicator)
                    model.Add(sum(works_shift_days) == 0).OnlyEnforceIf(shift_indicator.Not())
                    current_week_shifts[shift_code] = shift_indicator
            
            # Determine which shift types the employee works in next week
            next_week_shifts = {}
            for shift_code in rotation_shifts:
                works_shift_days = []
                
                for d in next_week:
                    weekday = d.weekday()
                    
                    # Regular team shift (weekday)
                    if weekday < 5 and (emp.id, d) in employee_active:
                        if (team.id, week_idx + 1, shift_code) in team_shift:
                            works_shift_days.append(
                                model.NewBoolVar(f"emp{emp.id}_w{week_idx+1}_d{d.day}_{shift_code}_regular")
                            )
                            model.AddMultiplicationEquality(
                                works_shift_days[-1],
                                [team_shift[(team.id, week_idx + 1, shift_code)], employee_active[(emp.id, d)]]
                            )
                    
                    # Regular team shift (weekend)
                    elif weekday >= 5 and (emp.id, d) in employee_weekend_shift:
                        if (team.id, week_idx + 1, shift_code) in team_shift:
                            works_shift_days.append(
                                model.NewBoolVar(f"emp{emp.id}_w{week_idx+1}_d{d.day}_{shift_code}_weekend")
                            )
                            model.AddMultiplicationEquality(
                                works_shift_days[-1],
                                [team_shift[(team.id, week_idx + 1, shift_code)], employee_weekend_shift[(emp.id, d)]]
                            )
                    
                    # Cross-team shift (weekday)
                    if weekday < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        works_shift_days.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    
                    # Cross-team shift (weekend)
                    elif weekday >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        works_shift_days.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                # Create indicator: employee works this shift type at least once next week
                if works_shift_days:
                    shift_indicator = model.NewBoolVar(f"emp{emp.id}_week{week_idx+1}_{shift_code}_indicator")
                    model.Add(sum(works_shift_days) >= 1).OnlyEnforceIf(shift_indicator)
                    model.Add(sum(works_shift_days) == 0).OnlyEnforceIf(shift_indicator.Not())
                    next_week_shifts[shift_code] = shift_indicator
            
            # Now check all possible transitions and penalize invalid ones
            for from_shift in rotation_shifts:
                if from_shift not in current_week_shifts:
                    continue
                
                for to_shift in rotation_shifts:
                    if to_shift not in next_week_shifts:
                        continue
                    
                    # Check if this transition is valid
                    if to_shift not in VALID_NEXT_SHIFTS[from_shift]:
                        # Invalid transition - create violation indicator
                        violation = model.NewBoolVar(
                            f"emp{emp.id}_week{week_idx}_to_{week_idx+1}_{from_shift}_to_{to_shift}_violation"
                        )
                        
                        # violation = 1 if (current_week has from_shift AND next_week has to_shift)
                        # This is equivalent to: violation = current_week_shifts[from_shift] AND next_week_shifts[to_shift]
                        model.AddMultiplicationEquality(
                            violation,
                            [current_week_shifts[from_shift], next_week_shifts[to_shift]]
                        )
                        
                        # Add penalty for this violation
                        penalty_var = model.NewIntVar(
                            0, 
                            ROTATION_ORDER_VIOLATION_PENALTY, 
                            f"emp{emp.id}_week{week_idx}_to_{week_idx+1}_{from_shift}_to_{to_shift}_penalty"
                        )
                        model.AddMultiplicationEquality(
                            penalty_var,
                            [violation, ROTATION_ORDER_VIOLATION_PENALTY]
                        )
                        rotation_order_penalties.append(penalty_var)
    
    return rotation_order_penalties


def add_employee_team_linkage_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    absences: List[Absence],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar] = None,
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar] = None
):
    """
    HARD CONSTRAINT: Link employee_active to team shifts and enforce cross-team rules.
    
    - Team members CAN work when their team works (but not required to work every day)
    - Employees CANNOT work if their team doesn't have a shift (unless cross-team)
    - Employees cannot work when absent (applies to both regular and cross-team)
    - Cross-team workers must have at most ONE shift per day
    - ALL rest time and transition rules apply to cross-team assignments
    - CRITICAL: Employees must work the SAME shift type throughout each week (team-based model)
    """
    
    # Provide empty dicts if weekend variables not passed (backward compatibility)
    if employee_weekend_shift is None:
        employee_weekend_shift = {}
    if employee_cross_team_weekend is None:
        employee_cross_team_weekend = {}
    
    # For each employee
    for emp in employees:
        # Employees without team skip
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
        
        # For each day
        for d in dates:
            # Check if employee is absent
            is_absent = any(
                abs.employee_id == emp.id and abs.overlaps_date(d)
                for abs in absences
            )
            
            if is_absent:
                # Force inactive if absent (both regular and cross-team)
                if (emp.id, d) in employee_active:
                    model.Add(employee_active[(emp.id, d)] == 0)
                
                # Force weekend work to 0 if absent
                if (emp.id, d) in employee_weekend_shift:
                    model.Add(employee_weekend_shift[(emp.id, d)] == 0)
                
                # Also force all cross-team variables to 0 (weekday)
                for shift_code in shift_codes:
                    if (emp.id, d, shift_code) in employee_cross_team_shift:
                        model.Add(employee_cross_team_shift[(emp.id, d, shift_code)] == 0)
                
                # Also force all cross-team weekend variables to 0 (weekend)
                for shift_code in shift_codes:
                    if (emp.id, d, shift_code) in employee_cross_team_weekend:
                        model.Add(employee_cross_team_weekend[(emp.id, d, shift_code)] == 0)
        
        # CRITICAL FIX: Enforce that employees work the SAME shift type throughout each week
        # This is the core of the team-based model: team members work the same shift during a week
        # BUG FIX for issue: "einzelnen Schichten zwischen andere Schichten geplant"
        # (individual shifts scheduled between other shifts)
        for week_idx, week_dates in enumerate(weeks):
            # For each shift type, create a variable indicating if employee works that shift this week
            employee_week_shift = {}
            
            for shift_code in shift_codes:
                # Check if employee's team has this shift this week
                if (team.id, week_idx, shift_code) not in team_shift:
                    continue
                
                # Create a variable: does employee work this shift type this week?
                # This will be 1 if employee works ANY day during this week with this shift type
                week_shift_indicator = model.NewBoolVar(f"emp{emp.id}_week{week_idx}_shift{shift_code}")
                employee_week_shift[shift_code] = week_shift_indicator
                
                # Collect all days in this week where employee could work with this shift
                work_days_with_this_shift = []
                
                for d in week_dates:
                    if d.weekday() < 5:  # Weekday
                        if (emp.id, d) in employee_active:
                            # Create constraint: if team has this shift AND employee is active,
                            # then employee is working this shift type
                            is_working_this_shift = model.NewBoolVar(
                                f"emp{emp.id}_date{d}_shift{shift_code}"
                            )
                            model.AddMultiplicationEquality(
                                is_working_this_shift,
                                [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            work_days_with_this_shift.append(is_working_this_shift)
                    else:  # Weekend
                        if (emp.id, d) in employee_weekend_shift:
                            # Weekend shift
                            is_working_this_shift_weekend = model.NewBoolVar(
                                f"emp{emp.id}_date{d}_weekend_shift{shift_code}"
                            )
                            model.AddMultiplicationEquality(
                                is_working_this_shift_weekend,
                                [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                            )
                            work_days_with_this_shift.append(is_working_this_shift_weekend)
                
                # Link the week-level indicator to the day-level work indicators
                # week_shift_indicator = 1 if ANY of the work days use this shift
                if work_days_with_this_shift:
                    # If any day works this shift, the indicator must be 1
                    for work_var in work_days_with_this_shift:
                        model.Add(week_shift_indicator >= work_var)
                    # If no days work this shift, the indicator must be 0
                    model.Add(week_shift_indicator <= sum(work_days_with_this_shift))
            
            # CRITICAL CONSTRAINT: Employee can work AT MOST ONE shift type per week
            # This enforces the team-based model where all work days in a week use the same shift
            if employee_week_shift:
                model.Add(sum(employee_week_shift.values()) <= 1)
            
            # Now handle cross-team constraints that must also respect weekly shift consistency
            # Cross-team workers must also maintain the same shift type throughout a week
            # Track which cross-team shift types the employee uses this week
            cross_team_week_shifts = {}
            
            for shift_code in shift_codes:
                work_days_cross_team = []
                
                for d in week_dates:
                    if d.weekday() < 5 and (emp.id, d, shift_code) in employee_cross_team_shift:
                        work_days_cross_team.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    elif d.weekday() >= 5 and (emp.id, d, shift_code) in employee_cross_team_weekend:
                        work_days_cross_team.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                
                if work_days_cross_team:
                    # Create indicator for this cross-team shift type in this week
                    cross_shift_indicator = model.NewBoolVar(
                        f"emp{emp.id}_week{week_idx}_crossteam_{shift_code}"
                    )
                    cross_team_week_shifts[shift_code] = cross_shift_indicator
                    
                    # Link indicator to actual work days
                    for work_var in work_days_cross_team:
                        model.Add(cross_shift_indicator >= work_var)
                    model.Add(cross_shift_indicator <= sum(work_days_cross_team))
            
            # Cross-team workers also can work at most ONE shift type per week
            if cross_team_week_shifts:
                model.Add(sum(cross_team_week_shifts.values()) <= 1)
            
            # CRITICAL FIX: If employee works both team shift AND cross-team in same week,
            # they must use the SAME shift type
            # This was previously commented as "already handled" but it was NOT enforced!
            if employee_week_shift and cross_team_week_shifts:
                # We need to ensure that the TOTAL across both team and cross-team is at most ONE shift type.
                # Combine the indicators for each shift type
                combined_week_shifts = {}
                for shift_code in shift_codes:
                    indicators = []
                    if shift_code in employee_week_shift:
                        indicators.append(employee_week_shift[shift_code])
                    if shift_code in cross_team_week_shifts:
                        indicators.append(cross_team_week_shifts[shift_code])
                    
                    if indicators:
                        # Create combined indicator: 1 if EITHER team or cross-team uses this shift
                        combined_indicator = model.NewBoolVar(
                            f"emp{emp.id}_week{week_idx}_combined_{shift_code}"
                        )
                        combined_week_shifts[shift_code] = combined_indicator
                        
                        # combined = 1 if ANY of the indicators is 1
                        for indicator in indicators:
                            model.Add(combined_indicator >= indicator)
                        model.Add(combined_indicator <= sum(indicators))
                
                # CRITICAL: Employee can work AT MOST ONE shift type per week
                # (considering both team and cross-team work)
                if combined_week_shifts:
                    model.Add(sum(combined_week_shifts.values()) <= 1)
            
            # FIX FOR BUG: Enforce that cross-team work cannot override team rotation on weekdays
            # Cross-team assignments should only be used to supplement team work, not replace it
            # On weekdays: if team has a shift this week AND employee works cross-team,
            # then employee must work the SAME shift type as their team
            # This prevents employees from skipping their team's rotation to work different shifts
            for shift_code in shift_codes:
                # If team has this shift type this week
                if (team.id, week_idx, shift_code) in team_shift:
                    # For each OTHER shift type
                    for other_shift_code in shift_codes:
                        if other_shift_code == shift_code:
                            continue  # Same shift is OK
                        
                        # Collect all cross-team weekday variables for this other shift type
                        cross_team_weekday_vars = []
                        
                        for d in week_dates:
                            if d.weekday() < 5:  # Weekday only
                                if (emp.id, d, other_shift_code) in employee_cross_team_shift:
                                    cross_team_weekday_vars.append(
                                        employee_cross_team_shift[(emp.id, d, other_shift_code)]
                                    )
                        
                        if cross_team_weekday_vars:
                            # HARD CONSTRAINT: If team works shift_code this week,
                            # employee CANNOT work other_shift_code via cross-team on weekdays
                            # Implementation: When team_shift[team, week, shift_code] = 1,
                            # force all cross_team[emp, weekday, other_shift_code] = 0
                            for cross_var in cross_team_weekday_vars:
                                model.Add(cross_var == 0).OnlyEnforceIf(team_shift[(team.id, week_idx, shift_code)])
        
        # For each day (original constraints for single shift per day)
        for d in dates:
            # CRITICAL: Employee can work at most ONE shift per day
            # Either their team's shift OR one cross-team shift, but not both
            if d.weekday() < 5:  # Weekday
                if (emp.id, d) in employee_active:
                    # Collect all possible shifts for this day
                    all_shifts = [employee_active[(emp.id, d)]]
                    
                    # Add all cross-team shift possibilities
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) in employee_cross_team_shift:
                            all_shifts.append(employee_cross_team_shift[(emp.id, d, shift_code)])
                    
                    # At most one shift active per day
                    if len(all_shifts) > 1:
                        model.Add(sum(all_shifts) <= 1)
            
            elif d.weekday() >= 5:  # Weekend - ensure single shift per day constraint
                # Weekend employees should not be assigned both their team shift AND cross-team shift
                if (emp.id, d) in employee_weekend_shift:
                    # Collect all possible shifts for this day
                    all_shifts = [employee_weekend_shift[(emp.id, d)]]
                    
                    # Add all cross-team weekend shift possibilities
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) in employee_cross_team_weekend:
                            all_shifts.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                    
                    # At most one shift active per day
                    if len(all_shifts) > 1:
                        model.Add(sum(all_shifts) <= 1)


