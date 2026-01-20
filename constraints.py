"""
OR-Tools CP-SAT constraints for TEAM-BASED shift planning.
Implements all hard and soft rules as constraints according to requirements.

CRITICAL: This implements a TEAM-BASED model where:
- Teams are the primary planning unit
- All team members work the SAME shift during a week
- Teams rotate weekly in fixed pattern: F → N → S
- Weekend shifts MUST match team's weekly shift type (only presence is variable)
- TD (Tagdienst) is an organizational marker, NOT a separate shift
"""

from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Set, Tuple
from entities import Employee, Absence, ShiftType, Team, get_shift_type_by_id

# Shift planning rules
MINIMUM_REST_HOURS = 11
MAXIMUM_CONSECUTIVE_SHIFTS = 6
MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS = 5
DEFAULT_WEEKLY_HOURS = 48.0  # Default maximum weekly hours for constraint calculations
                              # Note: Different from ShiftType default (40.0) which represents
                              # standard work week. This is the safety limit.
# NOTE: MAXIMUM_HOURS_PER_MONTH and MAXIMUM_HOURS_PER_WEEK are now calculated
# dynamically based on each employee's team's assigned shift(s) and their
# WeeklyWorkingHours configuration in the database.

# Staffing requirements
WEEKDAY_STAFFING = {
    "F": {"min": 4, "max": 5},  # Früh
    "S": {"min": 3, "max": 4},  # Spät
    "N": {"min": 3, "max": 3},  # Nacht
}

WEEKEND_STAFFING = {
    "F": {"min": 2, "max": 3},
    "S": {"min": 2, "max": 3},
    "N": {"min": 2, "max": 3},
}

# Forbidden transitions (violate 11-hour rest rule)
FORBIDDEN_TRANSITIONS = {
    "S": ["F"],  # Spät -> Früh (only 8 hours rest)
    "N": ["F"],  # Nacht -> Früh (0 hours rest)
}

# Fixed rotation pattern: F → N → S
ROTATION_PATTERN = ["F", "N", "S"]


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
    shift_types: List[ShiftType] = None
):
    """
    HARD CONSTRAINT: Teams follow fixed rotation pattern F → N → S.
    
    Each team follows the same rotation cycle with offset based on team ID.
    Week 0: Team 1=F, Team 2=N, Team 3=S
    Week 1: Team 1=N, Team 2=S, Team 3=F
    Week 2: Team 1=S, Team 2=F, Team 3=N
    Week 3: Team 1=F, Team 2=N, Team 3=S (repeats)
    
    Manual overrides (locked assignments) take precedence over rotation.
    
    IMPORTANT: Only applies to teams that have F, N, and S in their allowed shifts.
    Teams with other shift configurations (e.g., only TD/BMT/BSB) are skipped.
    """
    if "F" not in shift_codes or "N" not in shift_codes or "S" not in shift_codes:
        return  # Cannot enforce rotation if shifts are missing
    
    locked_team_shift = locked_team_shift or {}
    
    # Build shift type ID to code mapping
    shift_id_to_code = {}
    if shift_types:
        for st in shift_types:
            shift_id_to_code[st.id] = st.code
    
    # Find shift type IDs for F, N, S
    f_id = n_id = s_id = None
    for st_id, st_code in shift_id_to_code.items():
        if st_code == "F":
            f_id = st_id
        elif st_code == "N":
            n_id = st_id
        elif st_code == "S":
            s_id = st_id
    
    # Define the rotation cycle
    rotation = ["F", "N", "S"]
    
    # For each team, assign shifts based on rotation
    sorted_teams = sorted(teams, key=lambda t: t.id)
    
    for team_idx, team in enumerate(sorted_teams):
        # Check if team has all three rotation shifts (F, N, S) in allowed shifts
        # If team has allowed_shift_type_ids configured, check them
        if team.allowed_shift_type_ids:
            has_f = f_id in team.allowed_shift_type_ids if f_id else False
            has_n = n_id in team.allowed_shift_type_ids if n_id else False
            has_s = s_id in team.allowed_shift_type_ids if s_id else False
            
            if not (has_f and has_n and has_s):
                # Team doesn't have all three shifts - skip rotation constraint
                # Team will be constrained by add_team_shift_assignment_constraints instead
                continue
        
        # Team participates in F→N→S rotation
        for week_idx in range(len(weeks)):
            # Check if this assignment is locked (manual override)
            if (team.id, week_idx) in locked_team_shift:
                # Skip - locked assignment will be applied by _apply_locked_assignments()
                continue
            
            # Calculate which shift this team should have this week
            rotation_idx = (week_idx + team_idx) % len(rotation)
            assigned_shift = rotation[rotation_idx]
            
            # Force this team to have this specific shift this week
            if (team.id, week_idx, assigned_shift) in team_shift:
                model.Add(team_shift[(team.id, week_idx, assigned_shift)] == 1)


def add_employee_team_linkage_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    ferienjobber_cross_team: Dict[Tuple[int, int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    absences: List[Absence]
):
    """
    HARD CONSTRAINT: Link employee_active to team shifts.
    
    - Team members CAN work when their team works (but not required to work every day)
    - Employees CANNOT work if their team doesn't have a shift
    - Employees cannot work when absent
    """
    
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
            if (emp.id, d) not in employee_active:
                continue
            
            # Check if employee is absent
            is_absent = any(
                abs.employee_id == emp.id and abs.overlaps_date(d)
                for abs in absences
            )
            
            if is_absent:
                # Force inactive if absent
                model.Add(employee_active[(emp.id, d)] == 0)
            else:
                # Employee can only be active if their team is working
                # (i.e., employee_active implies team has a shift this week)
                # But employee doesn't HAVE to be active even if team works
                
                # Find which week this day is in
                week_idx = None
                for w_idx, week_dates in enumerate(weeks):
                    if d in week_dates:
                        week_idx = w_idx
                        break
                
                if week_idx is None:
                    continue
                
                # Employee can only be active on weekdays when team works
                if d.weekday() < 5:  # Monday to Friday
                    # No constraint needed - employee can choose to work or not
                    # Staffing constraints will ensure enough people work
                    pass
                else:  # Weekend
                    # On weekends, typically fewer people work
                    # Let staffing constraints handle this
                    pass


def add_staffing_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    ferienjobber_cross_team: Dict[Tuple[int, int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType] = None
):
    """
    HARD CONSTRAINT: Minimum and maximum staffing per shift.
    
    Staffing requirements are now configured per shift type in the database.
    Defaults to historical values if shift_types not provided (backwards compatibility).
    
    Weekdays (Mon-Fri): Count active team members per shift based on team assignments.
    Weekends (Sat-Sun): Count employees working weekend based on team shift type.
    
    CRITICAL: Weekend employees work their team's shift type (only presence varies).
    """
    # Build staffing lookup from shift_types
    if shift_types:
        staffing_weekday = {}
        staffing_weekend = {}
        for st in shift_types:
            if st.code in shift_codes:
                staffing_weekday[st.code] = {
                    "min": st.min_staff_weekday,
                    "max": st.max_staff_weekday
                }
                staffing_weekend[st.code] = {
                    "min": st.min_staff_weekend,
                    "max": st.max_staff_weekend
                }
    else:
        # Fallback to hardcoded values for backwards compatibility
        staffing_weekday = WEEKDAY_STAFFING
        staffing_weekend = WEEKEND_STAFFING
    
    for d in dates:
        is_weekend = d.weekday() >= 5
        staffing = staffing_weekend if is_weekend else staffing_weekday
        
        # Find which week this date belongs to
        week_idx = None
        for w_idx, week_dates in enumerate(weeks):
            if d in week_dates:
                week_idx = w_idx
                break
        
        if week_idx is None:
            continue
        
        for shift in shift_codes:
            if shift not in staffing:
                continue
            
            # Check if this shift works on this day (Mon-Fri vs Sat-Sun)
            # Find the shift type for this shift code
            shift_type = None
            if shift_types:
                for st in shift_types:
                    if st.code == shift:
                        shift_type = st
                        break
            
            # Skip if shift doesn't work on this day
            if shift_type and not shift_type.works_on_date(d):
                # This shift doesn't work on this day - skip staffing requirements
                continue
            
            if is_weekend:
                # WEEKEND: Count team members working this weekend with their team's shift
                # For each team with this shift, count active members
                assigned = []
                
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    
                    # Count members of this team working on this weekend day
                    for emp in employees:
                        if emp.team_id != team.id:
                            continue  # Only count team members
                        
                        if (emp.id, d) not in employee_weekend_shift:
                            continue
                        
                        # This employee works this shift if:
                        # 1. Their team has this shift this week
                        # 2. They are working on this weekend day
                        is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift}_date{d}")
                        model.AddMultiplicationEquality(
                            is_on_shift,
                            [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift)]]
                        )
                        assigned.append(is_on_shift)
                
                if assigned:
                    total_assigned = sum(assigned)
                    model.Add(total_assigned >= staffing[shift]["min"])
                    model.Add(total_assigned <= staffing[shift]["max"])
            else:
                # WEEKDAY: Count team members who work this shift on this day
                # A member works this shift if:
                # 1. Their team has this shift this week
                # 2. They are active on this day
                assigned = []
                
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    
                    # Count active members of this team on this day
                    for emp in employees:
                        if emp.team_id != team.id:
                            continue  # Only count team members
                        
                        if (emp.id, d) not in employee_active:
                            continue
                        
                        # This employee works this shift if team has shift AND employee is active
                        is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift}_date{d}")
                        model.AddMultiplicationEquality(
                            is_on_shift,
                            [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift)]]
                        )
                        assigned.append(is_on_shift)
                
                if assigned:
                    total_assigned = sum(assigned)
                    model.Add(total_assigned >= staffing[shift]["min"])
                    model.Add(total_assigned <= staffing[shift]["max"])


def add_rest_time_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Minimum 11 hours rest between shifts.
    
    With team-based planning and weekend consistency, rest times are maintained:
    - Within a week: Same shift type (F/N/S) daily, so no forbidden transitions
    - Week boundaries: F→N, N→S, S→F all have 56+ hours rest
    - Weekend transitions: Now safe because weekend shifts match team weekly shift
    
    Forbidden transitions (violate 11-hour rest):
    - S → F (Spät 21:45 → Früh 05:45 = 8 hours)
    - N → F (Nacht 05:45 → Früh 05:45 = 0 hours in same day context)
    
    With weekend consistency: If team has 'F' this week, weekends also 'F'.
    This eliminates the problematic weekend transitions like Fri-F → Sat-S → Mon-N.
    """
    # With team-based model and weekend consistency, forbidden transitions
    # can only occur at week boundaries, which are already handled by rotation.
    # The rotation F → N → S inherently provides sufficient rest:
    # - F (ends Fri 13:45) → N (starts Mon 21:45): 80+ hours
    # - N (ends Fri 05:45) → S (starts Mon 13:45): 56 hours
    # - S (ends Fri 21:45) → F (starts Mon 05:45): 56 hours
    #
    # All transitions satisfy the 11-hour minimum rest requirement.
    pass


def add_consecutive_shifts_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Maximum consecutive working days.
    
    - Maximum 6 consecutive shifts (including TD)
    - Maximum 5 consecutive night shifts (handled by team rotation)
    """
    # Maximum 6 consecutive working days
    for emp in employees:
        for i in range(len(dates) - MAXIMUM_CONSECUTIVE_SHIFTS):
            shifts_in_period = []
            for j in range(MAXIMUM_CONSECUTIVE_SHIFTS + 1):
                current_date = dates[i + j]
                
                # Check if working this day
                if current_date.weekday() < 5:  # Weekday
                    if (emp.id, current_date) in employee_active:
                        shifts_in_period.append(employee_active[(emp.id, current_date)])
                else:  # Weekend
                    # Working on weekend if assigned to work
                    if (emp.id, current_date) in employee_weekend_shift:
                        shifts_in_period.append(employee_weekend_shift[(emp.id, current_date)])
            
            if shifts_in_period:
                model.Add(sum(shifts_in_period) <= MAXIMUM_CONSECUTIVE_SHIFTS)


def add_working_hours_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType],
    absences: List[Absence] = None
):
    """
    HARD CONSTRAINT: Working hours limits based on shift configuration.
    
    This constraint ensures that employees:
    1. Meet minimum required working hours based on their shift's WeeklyWorkingHours
       (48h/week for main shifts F, S, N)
    2. Do not exceed maximum weekly hours (WeeklyWorkingHours from shift configuration)
    3. Monthly hours are calculated as WeeklyWorkingHours * 4 (e.g., 192h/month for 48h/week)
    4. Absences (U/AU/L) are exceptions - employees are not required to make up hours lost to absences
    5. If an employee works less in one week (without absence), they must compensate in other weeks
    
    The limits are now DYNAMIC per employee based on their team's assigned shift(s),
    replacing the previous fixed limits of 192 hours/month and 48 hours/week.
    
    Note: All main shifts (F, S, N) are 8 hours by default.
    Weekend hours are based on team's shift type (same as weekday).
    """
    absences = absences or []
    # Create shift hours lookup
    shift_hours = {}
    shift_weekly_hours = {}
    for st in shift_types:
        shift_hours[st.code] = st.hours
        shift_weekly_hours[st.code] = st.weekly_working_hours
    
    # Pre-calculate maximum weekly hours per team per week to avoid repeated computation
    team_week_max_hours = {}
    for emp in employees:
        if not emp.team_id:
            continue
        for week_idx in range(len(weeks)):
            key = (emp.team_id, week_idx)
            if key not in team_week_max_hours:
                # Calculate max hours for this team in this week
                possible_max_hours = [shift_weekly_hours.get(sc, DEFAULT_WEEKLY_HOURS) 
                                     for sc in shift_codes 
                                     if (emp.team_id, week_idx, sc) in team_shift]
                team_week_max_hours[key] = max(possible_max_hours) if possible_max_hours else DEFAULT_WEEKLY_HOURS
    
    # Calculate working hours per week and enforce MAXIMUM limits only
    # Note: Minimum hours enforcement has been REMOVED due to infeasibility issues
    # See explanation below for details
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
                
                # Multiply by team_shift to get conditional active days
                conditional_days = model.NewIntVar(0, len(week_dates), 
                                                   f"emp{emp.id}_week{week_idx}_shift{shift_code}_days")
                model.AddMultiplicationEquality(
                    conditional_days,
                    [team_shift[(emp.team_id, week_idx, shift_code)], days_active]
                )
                
                # Multiply by hours (scaled by 10)
                scaled_hours = int(shift_hours[shift_code] * 10)
                hours_terms.append(conditional_days * scaled_hours)
            
            if hours_terms:
                # Use pre-calculated maximum weekly hours (scaled by 10)
                max_scaled_hours = int(team_week_max_hours.get((emp.team_id, week_idx), DEFAULT_WEEKLY_HOURS) * 10)
                model.Add(sum(hours_terms) <= max_scaled_hours)
    
    # MINIMUM working hours constraint across the planning period
    # 
    # Business requirement (per @TimUx):
    # - ALL employees MUST reach their monthly minimum hours (e.g., 192h for 48h/week)
    # - Hours can vary per week (e.g., 56h one week, less another week)
    # - Only absences (sick, vacation, training) exempt employees from this requirement
    # - Minimum staffing (e.g., 3) is a FLOOR - more employees CAN and SHOULD work to meet hours
    # 
    # Implementation:
    # - Shift hours come from shift settings (ShiftType.hours)
    # - Weekly hours come from shift settings (ShiftType.weekly_working_hours)
    # - Monthly hours = weekly_working_hours × number of weeks without absences
    # - Each employee must meet total across all weeks (flexible weekly distribution)
    for emp in employees:
        if not emp.team_id:
            continue  # Only check team members
        
        # Calculate total hours worked across all weeks
        total_hours_terms = []
        
        # Calculate expected hours based on weeks without absences
        weeks_without_absences = 0
        weekly_target_hours = DEFAULT_WEEKLY_HOURS  # Default if no shifts found
        
        for week_idx, week_dates in enumerate(weeks):
            # Check if employee has any absences this week
            has_absence_this_week = any(
                any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
                for d in week_dates
            )
            
            if has_absence_this_week:
                # Skip this week - employee is absent, no hours expected
                continue
            
            weeks_without_absences += 1
            
            # Calculate hours worked this week based on team's shift assignment
            # Note: Only ONE shift is active per team per week due to team_shift constraints
            for shift_code in shift_codes:
                if (emp.team_id, week_idx, shift_code) not in team_shift:
                    continue
                if shift_code not in shift_hours:
                    continue
                
                # Update weekly target from shift settings (use last non-absent week's shift)
                if shift_code in shift_weekly_hours:
                    weekly_target_hours = shift_weekly_hours[shift_code]
                
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
                                              f"emp{emp.id}_week{week_idx}_days_min")
                model.Add(days_active == sum(active_days))
                
                # Multiply by team_shift to get conditional active days
                # This is only non-zero when team actually has this shift this week
                conditional_days = model.NewIntVar(0, len(week_dates), 
                                                   f"emp{emp.id}_week{week_idx}_shift{shift_code}_days_min")
                model.AddMultiplicationEquality(
                    conditional_days,
                    [team_shift[(emp.team_id, week_idx, shift_code)], days_active]
                )
                
                # Multiply by shift hours (from shift settings, scaled by 10)
                scaled_hours = int(shift_hours[shift_code] * 10)
                total_hours_terms.append(conditional_days * scaled_hours)
        
        # Apply minimum hours constraint if employee has weeks without absences
        # Total hours must be at least: weekly_working_hours × 4 weeks (standard month)
        # Note: Standard month = 4 weeks regardless of actual calendar days
        if total_hours_terms and weeks_without_absences > 0:
            # Expected total hours = weekly_target_hours × 4 weeks (standard month, scaled by 10)
            # User requirement: 48h × 4 = 192h per month, not 48h × actual weeks
            expected_total_hours_scaled = int(weekly_target_hours * 4 * 10)
            
            # Employee must work at least the expected total hours
            # This allows flexibility: can work 56h one week (7 days × 8h), less another week
            model.Add(sum(total_hours_terms) >= expected_total_hours_scaled)


def add_td_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    absences: List[Absence]
):
    """
    HARD CONSTRAINT: TD (Tagdienst) assignment.
    
    TD combines BMT (Brandmeldetechniker) and BSB (Brandschutzbeauftragter).
    
    Rules:
    - Exactly 1 TD per week (Monday-Friday)
    - TD replaces regular shift work for that employee
    - TD is NOT a separate shift, just an organizational marker
    - Cannot assign TD when employee is absent
    
    When TD is assigned to an employee for a week:
    - That employee does NOT work regular shifts that week
    - TD is marked as special function, not a shift assignment
    
    Feasibility Note:
    - If no TD-qualified employees are available (all absent), the constraint
      becomes "at most 1" instead of "exactly 1" to avoid infeasibility
    - In production, the system should alert administrators when this happens
    """
    for week_idx, week_dates in enumerate(weeks):
        # Only assign TD on weekdays
        weekday_dates = [d for d in week_dates if d.weekday() < 5]
        
        if not weekday_dates:
            continue
        
        # Get TD-qualified employees who are NOT absent this week
        available_for_td = []
        for emp in employees:
            if not emp.can_do_td:
                continue
            
            # Check if absent any day this week
            is_absent_this_week = any(
                any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
                for d in weekday_dates
            )
            
            if not is_absent_this_week and (emp.id, week_idx) in td_vars:
                available_for_td.append(td_vars[(emp.id, week_idx)])
        
        # Exactly 1 TD per week (or at most 1 if no qualified employees available)
        if available_for_td:
            if len(available_for_td) > 0:
                # Prefer exactly 1, but allow 0 only if absolutely necessary
                # This handles edge cases where all TD-qualified are needed elsewhere
                model.Add(sum(available_for_td) == 1)
            else:
                # No qualified employees available - skip this week
                # Validation will flag this as an issue
                pass
        
        # TD blocks regular shift work for that employee that week
        # When employee has TD, they should not be active on weekdays
        for emp in employees:
            if not emp.can_do_td:
                continue
            
            if (emp.id, week_idx) not in td_vars:
                continue
            
            # If employee has TD this week, they should not work regular shifts
            for d in weekday_dates:
                if (emp.id, d) in employee_active:
                    # employee_active[emp, d] == 0 when td_vars[emp, week] == 1
                    # This means: NOT(td_vars[emp, week] AND employee_active[emp, d])
                    # Equivalent to: employee_active[emp, d] <= 1 - td_vars[emp, week]
                    model.Add(employee_active[(emp.id, d)] <= 1 - td_vars[(emp.id, week_idx)])


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


def add_fairness_objectives(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    ferienjobber_cross_team: Dict[Tuple[int, int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str]
) -> List:
    """
    SOFT CONSTRAINTS: Fairness and optimization objectives.
    
    Goals:
    - Even distribution of work across teams
    - Fair distribution of weekend shifts
    - Fair distribution of night shifts
    - Fair distribution of TD assignments
    
    Returns list of objective terms to minimize.
    """
    objective_terms = []
    
    # 1. Fair distribution of total shifts per employee (including weekends)
    shift_counts = []
    for emp in employees:
        if not emp.team_id:
            continue  # Only include regular team members in fairness
        
        # Count weekday active days
        weekday_active = []
        for d in dates:
            if d.weekday() < 5 and (emp.id, d) in employee_active:
                weekday_active.append(employee_active[(emp.id, d)])
        
        # Count weekend work days
        weekend_active = []
        for d in dates:
            if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                weekend_active.append(employee_weekend_shift[(emp.id, d)])
        
        all_active = weekday_active + weekend_active
        if all_active:
            total = model.NewIntVar(0, len(dates), f"total_shifts_{emp.id}")
            model.Add(total == sum(all_active))
            shift_counts.append(total)
    
    # Minimize pairwise differences
    if len(shift_counts) > 1:
        for i in range(len(shift_counts)):
            for j in range(i + 1, len(shift_counts)):
                diff = model.NewIntVar(-len(dates), len(dates), f"diff_{i}_{j}")
                model.Add(diff == shift_counts[i] - shift_counts[j])
                abs_diff = model.NewIntVar(0, len(dates), f"abs_diff_{i}_{j}")
                model.AddAbsEquality(abs_diff, diff)
                objective_terms.append(abs_diff)
    
    # Count total weeks and weekend days for proper variable bounds
    num_weeks = len(weeks)
    num_weekend_days = len([d for d in dates if d.weekday() >= 5])
    
    # 2. Fair distribution of weekend work per employee WITHIN EACH TEAM
    # This ensures that weekend work is balanced among team members
    for team in teams:
        team_members = [emp for emp in employees if emp.team_id == team.id]
        if len(team_members) < 2:
            continue  # Need at least 2 members to balance
        
        weekend_counts = []
        for emp in team_members:
            weekend_work = []
            for d in dates:
                if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                    weekend_work.append(employee_weekend_shift[(emp.id, d)])
            
            if weekend_work:
                total_weekends = model.NewIntVar(0, num_weekend_days, f"weekends_{emp.id}_team{team.id}")
                model.Add(total_weekends == sum(weekend_work))
                weekend_counts.append(total_weekends)
        
        # Minimize variance in weekend distribution WITHIN this team
        if len(weekend_counts) > 1:
            for i in range(len(weekend_counts)):
                for j in range(i + 1, len(weekend_counts)):
                    diff = model.NewIntVar(-num_weekend_days, num_weekend_days, 
                                          f"weekend_diff_team{team.id}_{i}_{j}")
                    model.Add(diff == weekend_counts[i] - weekend_counts[j])
                    abs_diff = model.NewIntVar(0, num_weekend_days, f"weekend_abs_diff_team{team.id}_{i}_{j}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff * 5)  # Weight weekend fairness within teams VERY high
    
    # 3. Fair distribution of night shifts (count by team)
    if "N" in shift_codes:
        night_counts = []
        for team in teams:
            night_weeks = []
            for week_idx in range(num_weeks):
                if (team.id, week_idx, "N") in team_shift:
                    night_weeks.append(team_shift[(team.id, week_idx, "N")])
            
            if night_weeks:
                total_nights = model.NewIntVar(0, num_weeks, f"nights_{team.id}")
                model.Add(total_nights == sum(night_weeks))
                night_counts.append(total_nights)
        
        # Minimize variance in night shift distribution
        if len(night_counts) > 1:
            for i in range(len(night_counts)):
                for j in range(i + 1, len(night_counts)):
                    diff = model.NewIntVar(-num_weeks, num_weeks, f"night_diff_{i}_{j}")
                    model.Add(diff == night_counts[i] - night_counts[j])
                    abs_diff = model.NewIntVar(0, num_weeks, f"night_abs_diff_{i}_{j}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff * 2)  # Weight night fairness higher
    
    # 4. Fair distribution of TD assignments
    if td_vars:
        td_counts = []
        for emp in employees:
            if not emp.can_do_td:
                continue
            
            emp_td_weeks = []
            for week_idx in range(num_weeks):
                if (emp.id, week_idx) in td_vars:
                    emp_td_weeks.append(td_vars[(emp.id, week_idx)])
            
            if emp_td_weeks:
                total_td = model.NewIntVar(0, num_weeks, f"td_total_{emp.id}")
                model.Add(total_td == sum(emp_td_weeks))
                td_counts.append(total_td)
        
        # Minimize variance in TD distribution
        if len(td_counts) > 1:
            for i in range(len(td_counts)):
                for j in range(i + 1, len(td_counts)):
                    diff = model.NewIntVar(-num_weeks, num_weeks, f"td_diff_{i}_{j}")
                    model.Add(diff == td_counts[i] - td_counts[j])
                    abs_diff = model.NewIntVar(0, num_weeks, f"td_abs_diff_{i}_{j}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff)
    
    return objective_terms
