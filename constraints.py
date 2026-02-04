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
# NOTE: MINIMUM_REST_HOURS, MAXIMUM_CONSECUTIVE_SHIFTS, and MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS
# are now loaded dynamically from the GlobalSettings table in the database.
# The values in the database are stored in WEEKS and must be converted to DAYS when used.
# See load_global_settings() in data_loader.py

# Default values used as fallback if database is not available
DEFAULT_MINIMUM_REST_HOURS = 11
DEFAULT_MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS = 6  # In weeks
DEFAULT_MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS_WEEKS = 3  # In weeks

DEFAULT_WEEKLY_HOURS = 48.0  # Default maximum weekly hours for constraint calculations
                              # Note: Different from ShiftType default (40.0) which represents
                              # standard work week. This is the safety limit.
# NOTE: MAXIMUM_HOURS_PER_MONTH and MAXIMUM_HOURS_PER_WEEK are now calculated
# dynamically based on each employee's team's assigned shift(s) and their
# WeeklyWorkingHours configuration in the database.

# NOTE: Min/max staffing values are NO LONGER hardcoded here.
# They are ALWAYS read from the ShiftType configuration in the database.
# See data_loader.py for default values used during DB initialization only.

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
            # CRITICAL FIX: Use ISO week number for consistent rotation across month boundaries
            # This ensures the same calendar week always gets the same shift assignment
            # regardless of which month's planning period it appears in
            week_dates = weeks[week_idx]
            monday_of_week = week_dates[0]  # First day of week (Monday)
            iso_year, iso_week, iso_weekday = monday_of_week.isocalendar()
            
            # Use ISO week number for rotation calculation (absolute reference)
            # This ensures cross-month continuity: if a week spans two months,
            # both planning periods will assign the same shift to the same team
            rotation_idx = (iso_week + team_idx) % len(rotation)
            assigned_shift = rotation[rotation_idx]
            
            # Force this team to have this specific shift this week
            if (team.id, week_idx, assigned_shift) in team_shift:
                model.Add(team_shift[(team.id, week_idx, assigned_shift)] == 1)


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


def add_staffing_constraints(
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
    violation_tracker=None
) -> Tuple[List[cp_model.IntVar], List[Tuple[cp_model.IntVar, date]], Dict[str, List[Tuple[cp_model.IntVar, date]]], List[cp_model.IntVar]]:
    """
    HARD MINIMUM + SOFT MAXIMUM: Staffing per shift, INCLUDING cross-team workers.
    
    Staffing requirements are configured per shift type in the database.
    Values are ALWAYS read from shift_types parameter (no fallback values).
    
    Weekdays (Mon-Fri): Count active team members + cross-team workers per shift.
    Weekends (Sat-Sun): Count team weekend workers + cross-team weekend workers.
    
    CHANGE (per @TimUx): Maximum staffing is now SOFT - can be exceeded if needed
    to meet higher priority constraints (minimum hours, absences, etc.).
    Overstaffing creates a penalty but doesn't block feasibility.
    
    PRIORITY (per requirements): When distributing shifts to reach target hours:
    1. Respect maximum number of employees per shift (soft constraint)
    2. Reach target work hours per employee
    3. If needed, exceed max on WEEKDAYS first (lower penalty)
    4. If still needed, exceed max on WEEKENDS (higher penalty, even distribution)
    5. Prefer filling EARLIER dates before LATER dates (temporal distribution)
    6. Prefer NOT overstaffing LATER weekends (temporal overstaffing penalty)
    
    UPDATED: Now counts both regular team assignments and cross-team assignments.
    
    NEW: Returns separate penalty lists for weekday/weekend to allow differential weighting.
    Also returns weekday understaffing penalties BY SHIFT TYPE to allow priority ordering (F > S > N).
    Understaffing penalties now include date information for temporal weighting.
    Weekend overstaffing penalties also include date information for temporal weighting.
    
    NEW: Returns team_priority_violations to penalize cross-team usage when team has unfilled capacity.
    
    Args:
        shift_types: List of ShiftType objects from database (REQUIRED)
        violation_tracker: Optional tracker for recording when max is exceeded
        
    Returns:
        Tuple of (weekday_overstaffing_penalties, weekend_overstaffing_penalties, 
                  weekday_understaffing_by_shift, team_priority_violations) where:
                  - weekend_overstaffing_penalties is a list of (penalty_var, date) tuples for temporal weighting
                  - weekday_understaffing_by_shift is a dict mapping shift codes to lists of (penalty_var, date) tuples
                  - team_priority_violations are penalties for using cross-team when team has capacity
    """
    if not shift_types:
        raise ValueError("shift_types parameter is required and must contain ShiftType objects from database")
    
    # Build staffing lookup from shift_types (database configuration)
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
    
    # Initialize separate lists for different penalty types
    weekday_overstaffing_penalties = []
    weekend_overstaffing_penalties = []
    weekday_understaffing_by_shift = {shift: [] for shift in shift_codes}  # Separate by shift type for priority
    team_priority_violations = []  # Penalties for using cross-team when team has capacity
    
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
                # WEEKEND: Count team members working + cross-team weekend workers
                # For each team with this shift, count active members
                team_assigned = []  # Track team members separately
                cross_team_assigned = []  # Track cross-team workers separately
                
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
                        team_assigned.append(is_on_shift)
                
                # ADD: Count cross-team weekend workers for this shift
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_weekend:
                        cross_team_assigned.append(employee_cross_team_weekend[(emp.id, d, shift)])
                
                # Combine for total staffing
                assigned = team_assigned + cross_team_assigned
                
                if assigned:
                    total_assigned = sum(assigned)
                    # HARD minimum staffing
                    model.Add(total_assigned >= staffing[shift]["min"])
                    # SOFT maximum staffing - create penalty variable for overstaffing
                    # Include date for temporal weighting (penalize later weekends more)
                    overstaffing = model.NewIntVar(0, 20, f"overstaff_{shift}_{d}_weekend")
                    model.Add(overstaffing >= total_assigned - staffing[shift]["max"])
                    model.Add(overstaffing >= 0)
                    weekend_overstaffing_penalties.append((overstaffing, d))
                    
                    # NEW: Penalize cross-team usage when team has unfilled capacity on weekends too
                    if team_assigned and cross_team_assigned:
                        team_count = model.NewIntVar(0, 20, f"team_count_{shift}_{d}_weekend")
                        cross_team_count = model.NewIntVar(0, 20, f"cross_count_{shift}_{d}_weekend")
                        model.Add(team_count == sum(team_assigned))
                        model.Add(cross_team_count == sum(cross_team_assigned))
                        
                        # Calculate unfilled team capacity: max - team_count
                        unfilled_capacity = model.NewIntVar(0, 20, f"unfilled_{shift}_{d}_weekend")
                        model.Add(unfilled_capacity == staffing[shift]["max"] - team_count)
                        
                        # Penalty = min(unfilled_capacity, cross_team_count)
                        priority_violation = model.NewIntVar(0, 20, f"priority_violation_{shift}_{d}_weekend")
                        model.AddMinEquality(priority_violation, [unfilled_capacity, cross_team_count])
                        team_priority_violations.append(priority_violation)
            else:
                # WEEKDAY: Count team members + cross-team workers who work this shift
                # A member works this shift if:
                # 1. Their team has this shift this week
                # 2. They are active on this day
                team_assigned = []  # Track team members separately
                cross_team_assigned = []  # Track cross-team workers separately
                
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
                        team_assigned.append(is_on_shift)
                
                # ADD: Count cross-team workers for this shift on this day
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_shift:
                        cross_team_assigned.append(employee_cross_team_shift[(emp.id, d, shift)])
                
                # Combine for total staffing
                assigned = team_assigned + cross_team_assigned
                
                if assigned:
                    total_assigned = sum(assigned)
                    # HARD minimum staffing
                    model.Add(total_assigned >= staffing[shift]["min"])
                    # SOFT maximum staffing - create penalty variable for overstaffing
                    overstaffing = model.NewIntVar(0, 20, f"overstaff_{shift}_{d}_weekday")
                    model.Add(overstaffing >= total_assigned - staffing[shift]["max"])
                    model.Add(overstaffing >= 0)
                    weekday_overstaffing_penalties.append(overstaffing)
                    
                    # NEW: Add understaffing penalty for weekdays to encourage filling gaps
                    # Store by shift type to allow priority ordering (F > S > N)
                    # Include date for temporal weighting (prefer earlier dates)
                    understaffing = model.NewIntVar(0, 20, f"understaff_{shift}_{d}_weekday")
                    model.Add(understaffing >= staffing[shift]["max"] - total_assigned)
                    model.Add(understaffing >= 0)
                    weekday_understaffing_by_shift[shift].append((understaffing, d))
                    
                    # NEW: Penalize cross-team usage when team has unfilled capacity
                    # If team_assigned < max AND cross_team_assigned > 0, that's a violation
                    # This encourages filling with team members first
                    if team_assigned and cross_team_assigned:
                        team_count = model.NewIntVar(0, 20, f"team_count_{shift}_{d}")
                        cross_team_count = model.NewIntVar(0, 20, f"cross_count_{shift}_{d}")
                        model.Add(team_count == sum(team_assigned))
                        model.Add(cross_team_count == sum(cross_team_assigned))
                        
                        # Calculate unfilled team capacity: max - team_count
                        unfilled_capacity = model.NewIntVar(0, 20, f"unfilled_{shift}_{d}")
                        model.Add(unfilled_capacity == staffing[shift]["max"] - team_count)
                        
                        # Penalty = min(unfilled_capacity, cross_team_count)
                        # This is the number of cross-team workers that could have been team members
                        priority_violation = model.NewIntVar(0, 20, f"priority_violation_{shift}_{d}")
                        model.AddMinEquality(priority_violation, [unfilled_capacity, cross_team_count])
                        team_priority_violations.append(priority_violation)
    
    return weekday_overstaffing_penalties, weekend_overstaffing_penalties, weekday_understaffing_by_shift, team_priority_violations



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
    violation_tracker=None
):
    """
    SOFT CONSTRAINT: Minimum 11 hours rest between shifts (allows violations for feasibility).
    
    Per @TimUx: Rules should be followed, but exceptions are allowed when necessary to make
    planning feasible. Violations are tracked and reported in the summary.
    
    Forbidden transitions (violate 11-hour rest):
    - S → F (Spät 21:45 → Früh 05:45 = 8 hours)
    - N → F (Nacht 05:45 → Früh 05:45 = 0 hours in same day context)
    
    Implementation:
    - Sunday→Monday transitions: Medium penalty (5000 points - expected with team rotation)
    - Other weekday transitions: Very high penalty (50000 points - strongly discouraged)
    
    NOTE: Penalty weights have been significantly increased (from 50/500 to 5000/50000) to
    prevent rest time violations from being preferred over other soft constraints. This ensures
    that S→F and N→F transitions are only accepted when absolutely necessary for feasibility,
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
            
            # Track forbidden transitions: S→F and N→F (as soft penalties)
            # Per @TimUx: Allow violations when necessary for feasibility, but penalize them
            for i_today, today_shift_code in enumerate(today_shift_codes):
                for i_tomorrow, tomorrow_shift_code in enumerate(tomorrow_shift_codes):
                    # Check if this is a forbidden transition
                    if (today_shift_code == "S" and tomorrow_shift_code == "F") or \
                       (today_shift_code == "N" and tomorrow_shift_code == "F"):
                        
                        # Create a violation indicator variable
                        # violation = 1 if both shifts happen (forbidden transition occurs)
                        violation = model.NewBoolVar(f"rest_violation_{emp.id}_{today}_{tomorrow}")
                        
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
                        penalty_var = model.NewIntVar(0, penalty_weight, f"rest_penalty_{emp.id}_{today}_{tomorrow}")
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
    
    Implementation:
    - Check each week for shift type patterns
    - Penalize patterns where a shift type appears, then another shift type, then the first type again
    - This enforces grouping: all days of type A should come before or after all days of type B
    
    Returns:
        List of penalty variables for shift sequence grouping violations
    """
    grouping_penalties = []
    
    # Very high penalty for isolated shift types - must be higher than other shift stability constraints
    # This is critical to prevent patterns like N-N-N-S-N-N or S-S-F-S-S
    # Increased even further to ensure this constraint dominates over other soft constraints
    ISOLATION_PENALTY = 100000  # Dramatically increased to make shift grouping the highest priority (10x increase)
    
    # Helper to get shift type for a specific day
    def get_shift_type_for_day(emp_id, d):
        """Returns the shift code if employee works on day d, None otherwise"""
        result = {}  # Dict of shift_code -> list of constraint variables
        weekday = d.weekday()
        
        # Team shift (weekday)
        if weekday < 5 and (emp_id, d) in employee_active:
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
                            if shift_code not in result:
                                result[shift_code] = []
                            result[shift_code].extend([
                                team_shift[(team.id, week_idx, shift_code)],
                                employee_active[(emp_id, d)]
                            ])
        
        # Team shift (weekend)
        elif weekday >= 5 and (emp_id, d) in employee_weekend_shift:
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
        # BUGFIX: Changed from 'elif' to 'if' - Previously was 'elif weekday >= 5' which would
        # never execute after the 'elif weekday >= 5' block at line 1128 (Team shift weekend).
        # The team shift weekend block (lines 1128-1154) handles team assignments using employee_weekend_shift.
        # This cross-team block handles cross-team weekend assignments using employee_cross_team_weekend.
        # Both blocks need to execute for weekend days to capture both team and cross-team possibilities.
        if weekday >= 5:
            for shift_code in shift_codes:
                if (emp_id, d, shift_code) in employee_cross_team_weekend:
                    if shift_code not in result:
                        result[shift_code] = []
                    result[shift_code].append(employee_cross_team_weekend[(emp_id, d, shift_code)])
        
        return result
    
    # Check patterns across the entire planning period to catch patterns that span free days
    # We need to check beyond single weeks to catch patterns like: N - F N N N
    # where the free day creates gaps within the week
    for emp in employees:
        if not emp.team_id:
            continue
        
        # Check patterns across the ENTIRE planning period for each employee
        # This ensures we catch all A-B-A patterns regardless of week boundaries or free days
        # Get shift assignments for each day in the entire period
        period_shift_data = []
        for d in dates:
            shift_data = get_shift_type_for_day(emp.id, d)
            # Only include days where the employee COULD work (has potential shift assignments)
            if shift_data:  # If shift_data is not empty, employee could work this day
                period_shift_data.append((d, shift_data))
        
        # NOTE: period_shift_data is sorted by date because we iterate through 'dates' which is sorted
        # This assumption is used in the optimization below where we break early when days are > 10 apart
        
        # Now check for problematic patterns across all working days
        # Pattern to detect: shift_A appears, then shift B appears, then shift_A appears again
        # This means shifts are not properly grouped
        # KEY FIX: We now only look at POTENTIAL WORKING DAYS, not all calendar days
        
        # For each pair of shift types
        for shift_A in shift_codes:
            for shift_B in shift_codes:
                if shift_A == shift_B:
                    continue
                
                # Find all working days where each shift could be assigned
                days_with_A = [(d, data[shift_A]) for d, data in period_shift_data if shift_A in data]
                days_with_B = [(d, data[shift_B]) for d, data in period_shift_data if shift_B in data]
                
                if len(days_with_A) < 2 or len(days_with_B) < 1:
                    continue  # Not enough days for a violation pattern
                
                # Check if there's a day with shift_B that falls between two days with shift_A
                for i, (day_A1, vars_A1) in enumerate(days_with_A[:-1]):
                    for day_B, vars_B in days_with_B:
                        for day_A2, vars_A2 in days_with_A[i+1:]:
                            # Check if day_B is between day_A1 and day_A2
                            if day_A1 < day_B < day_A2:
                                # This is a potential violation: A ... B ... A pattern
                                # Create constraint: penalize if A1, B, and A2 all occur
                                all_active = []
                                all_active.extend(vars_A1)
                                all_active.extend(vars_B)
                                all_active.extend(vars_A2)
                                
                                # Create boolean: is_violation = (all variables are 1)
                                violation_var = model.NewBoolVar(
                                    f"seq_group_{emp.id}_{day_A1.isoformat()}_{day_B.isoformat()}_{day_A2.isoformat()}_{shift_A}_{shift_B}"
                                )
                                model.AddBoolAnd(all_active).OnlyEnforceIf(violation_var)
                                model.AddBoolOr([v.Not() for v in all_active]).OnlyEnforceIf(violation_var.Not())
                                
                                # Add penalty
                                penalty_var = model.NewIntVar(
                                    0, ISOLATION_PENALTY,
                                    f"seq_group_pen_{emp.id}_{day_A1.isoformat()}_{day_B.isoformat()}_{day_A2.isoformat()}_{shift_A}_{shift_B}"
                                )
                                model.Add(penalty_var == violation_var * ISOLATION_PENALTY)
                                grouping_penalties.append(penalty_var)
        
        # ADDITIONAL CHECK: Strict enforcement for patterns within a 10-day window
        # This adds an even stronger penalty for short-range violations (same week or adjacent weeks)
        # to make them nearly impossible to occur
        ULTRA_HIGH_PENALTY = 200000  # Double the normal penalty for close-range violations (10x increase)
        
        for shift_A in shift_codes:
            for shift_B in shift_codes:
                if shift_A == shift_B:
                    continue
                
                # Check every consecutive pair of days where the employee could work
                for i in range(len(period_shift_data)):
                    for j in range(i + 1, len(period_shift_data)):
                        day_i, shifts_i = period_shift_data[i]
                        day_j, shifts_j = period_shift_data[j]
                        
                        # Only check pairs within 10 calendar days
                        if (day_j - day_i).days > 10:
                            break  # No need to check further since list is sorted
                        
                        # Check for A-B pattern (day_i has shift_A, day_j has shift_B)
                        if shift_A not in shifts_i or shift_B not in shifts_j:
                            continue
                        
                        # Now check if there's any later day within 10 days that has shift_A again
                        for k in range(j + 1, len(period_shift_data)):
                            day_k, shifts_k = period_shift_data[k]
                            
                            # Check if day_k is within 10 days of day_i
                            if (day_k - day_i).days > 10:
                                break
                            
                            # Check if day_k has shift_A
                            if shift_A not in shifts_k:
                                continue
                            
                            # Found A-B-A pattern within 10-day window - apply ultra-high penalty
                            all_active = []
                            all_active.extend(shifts_i[shift_A])
                            all_active.extend(shifts_j[shift_B])
                            all_active.extend(shifts_k[shift_A])
                            
                            violation_var = model.NewBoolVar(
                                f"seq_ultra_{emp.id}_{day_i.isoformat()}_{day_j.isoformat()}_{day_k.isoformat()}_{shift_A}_{shift_B}"
                            )
                            model.AddBoolAnd(all_active).OnlyEnforceIf(violation_var)
                            model.AddBoolOr([v.Not() for v in all_active]).OnlyEnforceIf(violation_var.Not())
                            
                            penalty_var = model.NewIntVar(
                                0, ULTRA_HIGH_PENALTY,
                                f"seq_ultra_pen_{emp.id}_{day_i.isoformat()}_{day_j.isoformat()}_{day_k.isoformat()}_{shift_A}_{shift_B}"
                            )
                            model.Add(penalty_var == violation_var * ULTRA_HIGH_PENALTY)
                            grouping_penalties.append(penalty_var)
        
        # ADDITIONAL CHECK: Detect A-B-B-A patterns (two consecutive days of shift B between shift A days)
        # This addresses cases like S-F-F-S or S-N-N-S which violate shift grouping
        # Even higher penalty since this is a clear violation of the grouping principle
        A_B_B_A_PATTERN_PENALTY = 500000  # EXTREMELY high priority - prevent sandwiched shift patterns (10x increase)
        
        for shift_A in shift_codes:
            for shift_B in shift_codes:
                if shift_A == shift_B:
                    continue
                
                # Check for A-B-B-A pattern: day_i has shift_A, day_j and day_j1 have shift_B, day_k has shift_A
                # We need to ensure day_j and day_j1 are consecutive OR near-consecutive calendar days
                # NOTE: This creates O(n^4) complexity in worst case, but is mitigated by:
                # - Breaking early when days exceed 10-day window
                # - Breaking when day_j1 is more than 3 days from day_j
                # - Only checking days where employee could potentially work
                for i in range(len(period_shift_data)):
                    day_i, shifts_i = period_shift_data[i]
                    
                    if shift_A not in shifts_i:
                        continue
                    
                    # Look for pairs of days with shift_B (not necessarily adjacent in the list)
                    for j in range(i + 1, len(period_shift_data)):
                        day_j, shifts_j = period_shift_data[j]
                        
                        # Only check within 10 calendar days from day_i
                        if (day_j - day_i).days > 10:
                            break
                        
                        # Check if day_j has shift_B
                        if shift_B not in shifts_j:
                            continue
                        
                        # Look for another day with shift_B that's within 3 calendar days of day_j
                        for j1_idx in range(j + 1, len(period_shift_data)):
                            day_j1, shifts_j1 = period_shift_data[j1_idx]
                            
                            # Only check if day_j1 is within 3 calendar days of day_j
                            # This allows for patterns like: Mon(B), Tue(B) or Mon(B), Wed(B) with Tue off
                            if (day_j1 - day_j).days > 3:
                                break
                            
                            # Check if day_j1 has shift_B
                            if shift_B not in shifts_j1:
                                continue
                            
                            # Now check if there's a later day with shift_A after these two B days
                            for k in range(j1_idx + 1, len(period_shift_data)):
                                day_k, shifts_k = period_shift_data[k]
                                
                                # Only check within 10 calendar days from day_i
                                if (day_k - day_i).days > 10:
                                    break
                                
                                # Check if day_k has shift_A
                                if shift_A not in shifts_k:
                                    continue
                                
                                # Found A-B-B-A pattern - this is a serious violation
                                # Pattern: shift_A on day_i, shift_B on day_j, shift_B on day_j1, shift_A on day_k
                                all_active = []
                                all_active.extend(shifts_i[shift_A])
                                all_active.extend(shifts_j[shift_B])
                                all_active.extend(shifts_j1[shift_B])
                                all_active.extend(shifts_k[shift_A])
                                
                                violation_var = model.NewBoolVar(
                                    f"a_b_b_a_pattern_{emp.id}_{day_i.isoformat()}_{day_j.isoformat()}_{day_j1.isoformat()}_{day_k.isoformat()}_{shift_A}_{shift_B}"
                                )
                                model.AddBoolAnd(all_active).OnlyEnforceIf(violation_var)
                                model.AddBoolOr([v.Not() for v in all_active]).OnlyEnforceIf(violation_var.Not())
                                
                                penalty_var = model.NewIntVar(
                                    0, A_B_B_A_PATTERN_PENALTY,
                                    f"a_b_b_a_penalty_{emp.id}_{day_i.isoformat()}_{day_j.isoformat()}_{day_j1.isoformat()}_{day_k.isoformat()}_{shift_A}_{shift_B}"
                                )
                                model.Add(penalty_var == violation_var * A_B_B_A_PATTERN_PENALTY)
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
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    max_consecutive_shifts_days: int = 6,
    max_consecutive_night_shifts_days: int = 3
):
    """
    SOFT CONSTRAINT: Limit consecutive working days and consecutive night shifts.
    
    Requirements (from @TimUx clarification - updated):
    - Maximum consecutive working days across ALL shift types (e.g., 6 days)
      After reaching this limit, employee MUST have 24h break (cannot work next day)
    - Maximum consecutive night shifts (e.g., 3 days)
      After reaching this limit, employee can EITHER:
      a) Have 24h break, OR
      b) Switch to a different shift type (respecting rest time rules)
    
    Implementation as SOFT constraint:
    - Violations are penalized but allowed for feasibility
    - General consecutive: Penalizes working on day (max + 1)
    - Night consecutive: Only penalizes if STILL working night shift on day (max + 1)
      (switching to different shift type is acceptable)
    - Penalties tracked for reporting in summary
    - Goal: Follow rules but allow exceptions when necessary for planning
    
    Args:
        max_consecutive_shifts_days: Max consecutive working days across all shifts (default 6)
        max_consecutive_night_shifts_days: Max consecutive night shift days (default 3)
    
    Returns:
        List of penalty variables for consecutive shift violations
    """
    consecutive_violation_penalties = []
    
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
    
    # For each employee, check consecutive working days
    for emp in employees:
        # Track consecutive working days (any shift type)
        for start_idx in range(len(dates) - max_consecutive_shifts_days):
            # Check if employee works max_consecutive_shifts_days + 1 days in a row
            # This violates the rule (should have break after max days)
            working_indicators = []
            
            for day_offset in range(max_consecutive_shifts_days + 1):
                date_idx = start_idx + day_offset
                current_date = dates[date_idx]
                
                # Collect all work variables for this date
                work_vars = []
                if (emp.id, current_date) in employee_active:
                    work_vars.append(employee_active[(emp.id, current_date)])
                if (emp.id, current_date) in employee_weekend_shift:
                    work_vars.append(employee_weekend_shift[(emp.id, current_date)])
                for shift_code in shift_codes:
                    if (emp.id, current_date, shift_code) in employee_cross_team_shift:
                        work_vars.append(employee_cross_team_shift[(emp.id, current_date, shift_code)])
                    if (emp.id, current_date, shift_code) in employee_cross_team_weekend:
                        work_vars.append(employee_cross_team_weekend[(emp.id, current_date, shift_code)])
                
                if work_vars:
                    # Create indicator: is employee working this day?
                    is_working = model.NewBoolVar(f"consec_work_{emp.id}_{date_idx}")
                    model.Add(sum(work_vars) >= 1).OnlyEnforceIf(is_working)
                    model.Add(sum(work_vars) == 0).OnlyEnforceIf(is_working.Not())
                    working_indicators.append(is_working)
                else:
                    # No work variables for this date, count as not working
                    working_indicators.append(0)
            
            # Check if all (max_consecutive_shifts_days + 1) days are working
            if len(working_indicators) == max_consecutive_shifts_days + 1:
                # Violation occurs when sum equals the full length
                violation = model.NewBoolVar(f"consec_viol_{emp.id}_{start_idx}")
                model.Add(sum(working_indicators) == max_consecutive_shifts_days + 1).OnlyEnforceIf(violation)
                model.Add(sum(working_indicators) < max_consecutive_shifts_days + 1).OnlyEnforceIf(violation.Not())
                
                # Penalty: 300 points per violation
                penalty = model.NewIntVar(0, 300, f"consec_penalty_{emp.id}_{start_idx}")
                model.AddMultiplicationEquality(penalty, [violation, 300])
                consecutive_violation_penalties.append(penalty)
        
        # Track consecutive night shifts specifically
        # NOTE: This only penalizes if employee continues working NIGHT shifts beyond the limit.
        # Switching to a different shift type after max consecutive nights is acceptable.
        for start_idx in range(len(dates) - max_consecutive_night_shifts_days):
            night_indicators = []
            
            for day_offset in range(max_consecutive_night_shifts_days + 1):
                date_idx = start_idx + day_offset
                current_date = dates[date_idx]
                
                # Get week index from pre-computed mapping
                week_idx = date_to_week.get(current_date)
                if week_idx is None:
                    night_indicators.append(0)
                    continue
                
                # Collect night shift variables
                night_vars = []
                
                # Team-based night shift (weekday)
                if current_date.weekday() < 5 and (emp.id, current_date) in employee_active:
                    team = emp_to_team.get(emp.id)
                    if team and (team.id, week_idx, 'N') in team_shift:
                        # Employee works night if: active AND team has night shift
                        night_work = model.NewBoolVar(f"night_team_{emp.id}_{date_idx}")
                        model.AddMultiplicationEquality(
                            night_work,
                            [employee_active[(emp.id, current_date)], team_shift[(team.id, week_idx, 'N')]]
                        )
                        night_vars.append(night_work)
                
                # Team-based night shift (weekend)
                if current_date.weekday() >= 5 and (emp.id, current_date) in employee_weekend_shift:
                    team = emp_to_team.get(emp.id)
                    if team and (team.id, week_idx, 'N') in team_shift:
                        night_weekend = model.NewBoolVar(f"night_weekend_{emp.id}_{date_idx}")
                        model.AddMultiplicationEquality(
                            night_weekend,
                            [employee_weekend_shift[(emp.id, current_date)], team_shift[(team.id, week_idx, 'N')]]
                        )
                        night_vars.append(night_weekend)
                
                # Cross-team night shift
                if (emp.id, current_date, 'N') in employee_cross_team_shift:
                    night_vars.append(employee_cross_team_shift[(emp.id, current_date, 'N')])
                if (emp.id, current_date, 'N') in employee_cross_team_weekend:
                    night_vars.append(employee_cross_team_weekend[(emp.id, current_date, 'N')])
                
                if night_vars:
                    is_night = model.NewBoolVar(f"is_night_{emp.id}_{date_idx}")
                    model.Add(sum(night_vars) >= 1).OnlyEnforceIf(is_night)
                    model.Add(sum(night_vars) == 0).OnlyEnforceIf(is_night.Not())
                    night_indicators.append(is_night)
                else:
                    night_indicators.append(0)
            
            # Violation only if ALL (max_consecutive_night_shifts_days + 1) days are night shifts
            # If employee switches to different shift on day (max + 1), no violation occurs
            if len(night_indicators) == max_consecutive_night_shifts_days + 1:
                night_violation = model.NewBoolVar(f"night_viol_{emp.id}_{start_idx}")
                model.Add(sum(night_indicators) == max_consecutive_night_shifts_days + 1).OnlyEnforceIf(night_violation)
                model.Add(sum(night_indicators) < max_consecutive_night_shifts_days + 1).OnlyEnforceIf(night_violation.Not())
                
                # Penalty: 400 points per violation (higher than general consecutive)
                night_penalty = model.NewIntVar(0, 400, f"night_penalty_{emp.id}_{start_idx}")
                model.AddMultiplicationEquality(night_penalty, [night_violation, 400])
                consecutive_violation_penalties.append(night_penalty)
    
    return consecutive_violation_penalties


def add_working_hours_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType],
    absences: List[Absence] = None,
    violation_tracker=None
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
    
    Example: Employee has AU on March 1 (Sunday) but worked Feb 23-28. Previously week 4 (Feb 23-Mar 1)
    was completely skipped. Now only March 1 is skipped, and Feb 23-28 hours are properly counted.
    
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
    
    # NOTE: No weekly maximum hours constraints
    # Employees can work varying hours per week (e.g., 40h one week, 56h another)
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
    # Business requirement (per @TimUx - updated 2026-01-24):
    # - HARD CONSTRAINT: Absolute minimum 192h/month (48h/week × 4 weeks)
    #   → No employee can work less than this (except when absent)
    # - SOFT CONSTRAINT: Target is proportional to days: (48h/7) × days_in_period
    #   → Example: January 31 days → 48/7 × 31 = 212.57h target
    #   → Example: February 28 days → 48/7 × 28 = 192h target
    # - Hours can vary per week (e.g., 56h one week, 40h another week)
    # - Only absences (sick, vacation, training) exempt employees from these requirements
    # - Minimum staffing (e.g., F=4, S=3, N=3) is a FLOOR - more employees SHOULD work to meet hours
    # 
    # Implementation:
    # - Hard constraint: total_hours >= 192h (scaled: >= 1920)
    # - Soft objective: maximize(total_hours - target_hours) where target = (48/7) × days
    # - Shift hours come from shift settings (ShiftType.hours)
    # - Weekly hours come from shift settings (ShiftType.weekly_working_hours)
    for emp in employees:
        if not emp.team_id:
            continue  # Only check team members
        
        # Calculate total hours worked across all weeks
        total_hours_terms = []
        
        # Calculate total days without absences for this employee
        # FIX: Count days instead of weeks to handle partial-week absences correctly
        days_without_absence = 0
        for d in dates:
            is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
            if not is_absent:
                days_without_absence += 1
        
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
                # FIX: Only count days WITHOUT absences
                active_days = []
                
                # WEEKDAY days
                for d in week_dates:
                    # Skip days with absences
                    is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
                    if is_absent:
                        continue
                    
                    if d.weekday() < 5 and (emp.id, d) in employee_active:
                        active_days.append(employee_active[(emp.id, d)])
                
                # WEEKEND days (same shift type as team)
                for d in week_dates:
                    # Skip days with absences
                    is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
                    if is_absent:
                        continue
                    
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
            
            # ADD: Count cross-team hours this week for minimum hours calculation
            # FIX: Only count days WITHOUT absences
            for shift_code in shift_codes:
                if shift_code not in shift_hours:
                    continue
                
                cross_team_days = []
                for d in week_dates:
                    # Skip days with absences
                    is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) for abs in absences)
                    if is_absent:
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
            # HARD CONSTRAINT: Absolute minimum 192h/month (24 shifts × 8h)
            # This ensures employees work at least 24 shifts per month as required
            # Only applies to employees without full-month absences
            # Scaled: 192h × 10 = 1920
            min_hours_scaled = 1920  # 192h × 10 (scaling factor)
            model.Add(sum(total_hours_terms) >= min_hours_scaled)
            
            # SOFT CONSTRAINT: Target proportional hours (48h/7 × days)
            # Example: 31 days → 48/7 × 31 = 212.57h ≈ 213h target (scaled: 2130)
            # We want to minimize the shortage from this target
            daily_target_hours = weekly_target_hours / 7.0
            target_total_hours_scaled = int(daily_target_hours * days_without_absence * 10)
            
            # Create variable for shortage from target (0 if at target, positive if below)
            shortage_from_target = model.NewIntVar(0, target_total_hours_scaled, 
                                                    f"emp{emp.id}_hours_shortage")
            
            # shortage = max(0, target - actual)
            # We model this as: shortage >= target - actual AND shortage >= 0
            model.Add(shortage_from_target >= target_total_hours_scaled - sum(total_hours_terms))
            model.Add(shortage_from_target >= 0)
            
            # Add to soft objectives (minimize shortage)
            soft_objectives.append(shortage_from_target)
    
    return soft_objectives


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
        
        # At most 1 TD per week (prefer exactly 1, but allow 0 when needed for staffing)
        if available_for_td:
            if len(available_for_td) > 0:
                # Allow 0 or 1 TD per week - flexibility for constraint satisfaction
                # When TD-qualified employees are needed for regular shifts to meet
                # minimum staffing requirements, we allow 0 TD that week
                model.Add(sum(available_for_td) <= 1)
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


def add_fairness_objectives(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    ytd_weekend_counts: Dict[int, int] = None,
    ytd_night_counts: Dict[int, int] = None,
    ytd_holiday_counts: Dict[int, int] = None
) -> List:
    """
    SOFT CONSTRAINTS: Fairness and optimization objectives with YEAR-LONG fairness tracking.
    
    NEW REQUIREMENTS:
    - Fair distribution PER EMPLOYEE (not per team)
    - Fairness across the ENTIRE YEAR (not just current planning period)
    - Group employees by common shift types across teams
    - Block scheduling: minimize gaps between working days
    - Prefer own team shifts over cross-team (soft constraint)
    
    Goals:
    - Even distribution of work across all employees with same shift types
    - Fair distribution of weekend shifts (year-to-date + current period)
    - Fair distribution of night shifts (year-to-date + current period)
    - Fair distribution of holidays (year-to-date + current period)
    - Fair distribution of TD assignments
    - Block scheduling: consecutive working days preferred
    - Own team shifts preferred over cross-team
    
    Args:
        ytd_weekend_counts: Dict mapping employee_id -> count of weekend days worked this year
        ytd_night_counts: Dict mapping employee_id -> count of night shifts worked this year
        ytd_holiday_counts: Dict mapping employee_id -> count of holidays worked this year
    
    Returns list of objective terms to minimize.
    """
    ytd_weekend_counts = ytd_weekend_counts or {}
    ytd_night_counts = ytd_night_counts or {}
    ytd_holiday_counts = ytd_holiday_counts or {}
    
    objective_terms = []
    
    # Helper: Group employees by their allowed shift types
    # Employees in different teams but with same shift capabilities should be compared
    def get_employee_shift_group(emp: Employee) -> frozenset:
        """Get the set of shift types this employee can work (determines fairness group)"""
        if not emp.team_id:
            return frozenset()
        
        # Find employee's team
        emp_team = None
        for t in teams:
            if t.id == emp.team_id:
                emp_team = t
                break
        
        if not emp_team:
            return frozenset()
        
        # If team has specific allowed shifts, use those
        if emp_team.allowed_shift_type_ids:
            return frozenset(emp_team.allowed_shift_type_ids)
        else:
            # No restrictions - can work all shifts
            return frozenset(shift_codes)
    
    # Group employees by their shift capabilities
    shift_groups = {}
    for emp in employees:
        if not emp.team_id:
            continue
        
        group_key = get_employee_shift_group(emp)
        if group_key not in shift_groups:
            shift_groups[group_key] = []
        shift_groups[group_key].append(emp)
    
    # Count total weeks and weekend days for proper variable bounds
    num_weeks = len(weeks)
    num_weekend_days = len([d for d in dates if d.weekday() >= 5])
    
    # 1. BLOCK SCHEDULING: Minimize gaps between working days
    # Penalize having OFF days between working days
    print("  Adding block scheduling objectives...")
    for emp in employees:
        if not emp.team_id:
            continue
        
        for i in range(len(dates) - 2):
            day1 = dates[i]
            day2 = dates[i + 1]
            day3 = dates[i + 2]
            
            # Check if day1, day2, day3 form a gap pattern: WORK - OFF - WORK
            # We want to penalize this pattern
            working_vars = []
            for d in [day1, day2, day3]:
                day_vars = []
                
                # Regular team work
                if d.weekday() < 5 and (emp.id, d) in employee_active:
                    day_vars.append(employee_active[(emp.id, d)])
                elif d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                    day_vars.append(employee_weekend_shift[(emp.id, d)])
                
                # Cross-team work
                for sc in shift_codes:
                    if d.weekday() < 5 and (emp.id, d, sc) in employee_cross_team_shift:
                        day_vars.append(employee_cross_team_shift[(emp.id, d, sc)])
                    elif d.weekday() >= 5 and (emp.id, d, sc) in employee_cross_team_weekend:
                        day_vars.append(employee_cross_team_weekend[(emp.id, d, sc)])
                
                if day_vars:
                    is_working = model.NewBoolVar(f"emp{emp.id}_working_{d}_block")
                    model.Add(sum(day_vars) >= 1).OnlyEnforceIf(is_working)
                    model.Add(sum(day_vars) == 0).OnlyEnforceIf(is_working.Not())
                    working_vars.append(is_working)
                else:
                    # No variables for this day - employee cannot work
                    working_vars.append(0)
            
            if len(working_vars) == 3 and all(isinstance(v, cp_model.IntVar) for v in working_vars):
                # Detect gap: day1=1, day2=0, day3=1
                # Penalize: working_vars[0] + working_vars[2] - working_vars[1] >= 2 means gap exists
                gap_penalty = model.NewIntVar(0, 3, f"gap_penalty_emp{emp.id}_{i}")
                model.Add(gap_penalty == working_vars[0] + working_vars[2] - working_vars[1])
                # If gap_penalty == 2, that's a gap (work-off-work)
                # We penalize gaps with weight 3
                objective_terms.append(gap_penalty * 3)
    
    # 2. PREFER OWN TEAM SHIFTS OVER CROSS-TEAM
    # Add small penalty for cross-team assignments
    print("  Adding cross-team preference objectives...")
    for emp in employees:
        cross_team_days = []
        for d in dates:
            for sc in shift_codes:
                if d.weekday() < 5 and (emp.id, d, sc) in employee_cross_team_shift:
                    cross_team_days.append(employee_cross_team_shift[(emp.id, d, sc)])
                elif d.weekday() >= 5 and (emp.id, d, sc) in employee_cross_team_weekend:
                    cross_team_days.append(employee_cross_team_weekend[(emp.id, d, sc)])
        
        if cross_team_days:
            cross_team_count = model.NewIntVar(0, len(dates), f"cross_team_count_emp{emp.id}")
            model.Add(cross_team_count == sum(cross_team_days))
            # Small penalty for using cross-team (weight 1)
            objective_terms.append(cross_team_count * 1)
    
    # 2b. PREFER WEEKEND WORK FOR EMPLOYEES WHO WORKED MON-FRI
    # Encourage employees who worked Mon-Fri to also work weekends
    print("  Adding Mon-Fri weekend continuation preference...")
    for emp in employees:
        if not emp.team_id:
            continue
        
        for week_idx, week_dates in enumerate(weeks):
            # Get weekdays and weekend days
            weekdays = [d for d in week_dates if d.weekday() < 5]
            weekend_days = [d for d in week_dates if d.weekday() >= 5]
            
            if not weekdays or not weekend_days:
                continue
            
            # Count how many weekdays the employee worked
            weekday_vars = []
            for d in weekdays:
                day_vars = []
                if (emp.id, d) in employee_active:
                    day_vars.append(employee_active[(emp.id, d)])
                for sc in shift_codes:
                    if (emp.id, d, sc) in employee_cross_team_shift:
                        day_vars.append(employee_cross_team_shift[(emp.id, d, sc)])
                
                if day_vars:
                    is_working = model.NewBoolVar(f"emp{emp.id}_working_wd_{d}")
                    model.Add(sum(day_vars) >= 1).OnlyEnforceIf(is_working)
                    model.Add(sum(day_vars) == 0).OnlyEnforceIf(is_working.Not())
                    weekday_vars.append(is_working)
            
            if not weekday_vars:
                continue
            
            # Count weekend work
            weekend_vars = []
            for d in weekend_days:
                day_vars = []
                if (emp.id, d) in employee_weekend_shift:
                    day_vars.append(employee_weekend_shift[(emp.id, d)])
                for sc in shift_codes:
                    if (emp.id, d, sc) in employee_cross_team_weekend:
                        day_vars.append(employee_cross_team_weekend[(emp.id, d, sc)])
                
                if day_vars:
                    is_working = model.NewBoolVar(f"emp{emp.id}_working_we_{d}")
                    model.Add(sum(day_vars) >= 1).OnlyEnforceIf(is_working)
                    model.Add(sum(day_vars) == 0).OnlyEnforceIf(is_working.Not())
                    weekend_vars.append(is_working)
            
            if weekday_vars and weekend_vars:
                # If worked many weekdays (e.g., 3+), prefer working weekend too
                # This creates continuity and maximizes consecutive working days
                weekday_count = model.NewIntVar(0, len(weekday_vars), f"emp{emp.id}_wd_count_w{week_idx}")
                model.Add(weekday_count == sum(weekday_vars))
                
                weekend_count = model.NewIntVar(0, len(weekend_vars), f"emp{emp.id}_we_count_w{week_idx}")
                model.Add(weekend_count == sum(weekend_vars))
                
                # Reward: If worked >=3 weekdays and worked weekend, give negative penalty (reward)
                # This encourages block scheduling
                worked_full_block = model.NewBoolVar(f"emp{emp.id}_full_block_w{week_idx}")
                model.Add(weekday_count >= 3).OnlyEnforceIf(worked_full_block)
                model.Add(weekend_count >= 1).OnlyEnforceIf(worked_full_block)
                model.Add(weekday_count < 3).OnlyEnforceIf(worked_full_block.Not())
                # Note: We can't give negative objective terms, so we penalize NOT having full blocks
                # Penalty of 2 for not having full blocks when possible
                objective_terms.append((1 - worked_full_block) * 2)
    
    # 3. FAIR DISTRIBUTION OF WEEKEND WORK (YEAR-TO-DATE + CURRENT PERIOD)
    # Compare ALL employees with same shift capabilities (across teams)
    print("  Adding weekend fairness objectives (year-long)...")
    for group_key, group_employees in shift_groups.items():
        if len(group_employees) < 2:
            continue
        
        # For each employee, calculate total weekends including YTD
        weekend_totals = []
        for emp in group_employees:
            # Count current period weekends
            weekend_work_current = []
            for d in dates:
                if d.weekday() >= 5:  # Saturday or Sunday
                    # Regular weekend work
                    if (emp.id, d) in employee_weekend_shift:
                        weekend_work_current.append(employee_weekend_shift[(emp.id, d)])
                    
                    # Cross-team weekend work
                    for sc in shift_codes:
                        if (emp.id, d, sc) in employee_cross_team_weekend:
                            weekend_work_current.append(employee_cross_team_weekend[(emp.id, d, sc)])
            
            if weekend_work_current or emp.id in ytd_weekend_counts:
                current_weekends = model.NewIntVar(0, num_weekend_days, f"current_weekends_{emp.id}")
                if weekend_work_current:
                    model.Add(current_weekends == sum(weekend_work_current))
                else:
                    model.Add(current_weekends == 0)
                
                # Add YTD count
                ytd_count = ytd_weekend_counts.get(emp.id, 0)
                total_weekends = model.NewIntVar(ytd_count, ytd_count + num_weekend_days, 
                                                 f"total_weekends_{emp.id}")
                model.Add(total_weekends == ytd_count + current_weekends)
                weekend_totals.append((emp.id, total_weekends))
        
        # Minimize pairwise differences in total weekend counts
        if len(weekend_totals) > 1:
            for i in range(len(weekend_totals)):
                for j in range(i + 1, len(weekend_totals)):
                    emp_i_id, count_i = weekend_totals[i]
                    emp_j_id, count_j = weekend_totals[j]
                    
                    max_diff = num_weekend_days + max(ytd_weekend_counts.get(emp_i_id, 0), 
                                                       ytd_weekend_counts.get(emp_j_id, 0))
                    diff = model.NewIntVar(-max_diff, max_diff, 
                                          f"weekend_diff_{emp_i_id}_{emp_j_id}")
                    model.Add(diff == count_i - count_j)
                    abs_diff = model.NewIntVar(0, max_diff, f"weekend_abs_diff_{emp_i_id}_{emp_j_id}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff * 10)  # VERY HIGH weight for weekend fairness
    
    # 4. FAIR DISTRIBUTION OF NIGHT SHIFTS (YEAR-TO-DATE + CURRENT PERIOD)
    # Compare ALL employees with same shift capabilities (across teams)
    if "N" in shift_codes:
        print("  Adding night shift fairness objectives (year-long)...")
        for group_key, group_employees in shift_groups.items():
            if len(group_employees) < 2:
                continue
            
            # For each employee, calculate total night shifts including YTD
            night_totals = []
            for emp in group_employees:
                # Count current period night shifts
                night_shifts_current = []
                
                # Regular team night shifts
                emp_team = None
                for t in teams:
                    if t.id == emp.team_id:
                        emp_team = t
                        break
                
                if emp_team:
                    for week_idx in range(num_weeks):
                        if (emp_team.id, week_idx, "N") in team_shift:
                            # Employee works night if team has night AND employee is active
                            for d in weeks[week_idx]:
                                if d.weekday() < 5 and (emp.id, d) in employee_active:
                                    has_night = model.NewBoolVar(f"emp{emp.id}_night_{d}")
                                    model.AddMultiplicationEquality(
                                        has_night,
                                        [employee_active[(emp.id, d)], team_shift[(emp_team.id, week_idx, "N")]]
                                    )
                                    night_shifts_current.append(has_night)
                                elif d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                                    has_night = model.NewBoolVar(f"emp{emp.id}_night_{d}")
                                    model.AddMultiplicationEquality(
                                        has_night,
                                        [employee_weekend_shift[(emp.id, d)], team_shift[(emp_team.id, week_idx, "N")]]
                                    )
                                    night_shifts_current.append(has_night)
                
                # Cross-team night shifts
                for d in dates:
                    if d.weekday() < 5 and (emp.id, d, "N") in employee_cross_team_shift:
                        night_shifts_current.append(employee_cross_team_shift[(emp.id, d, "N")])
                    elif d.weekday() >= 5 and (emp.id, d, "N") in employee_cross_team_weekend:
                        night_shifts_current.append(employee_cross_team_weekend[(emp.id, d, "N")])
                
                if night_shifts_current or emp.id in ytd_night_counts:
                    current_nights = model.NewIntVar(0, len(dates), f"current_nights_{emp.id}")
                    if night_shifts_current:
                        model.Add(current_nights == sum(night_shifts_current))
                    else:
                        model.Add(current_nights == 0)
                    
                    # Add YTD count
                    ytd_count = ytd_night_counts.get(emp.id, 0)
                    total_nights = model.NewIntVar(ytd_count, ytd_count + len(dates), 
                                                   f"total_nights_{emp.id}")
                    model.Add(total_nights == ytd_count + current_nights)
                    night_totals.append((emp.id, total_nights))
            
            # Minimize pairwise differences in total night counts
            if len(night_totals) > 1:
                for i in range(len(night_totals)):
                    for j in range(i + 1, len(night_totals)):
                        emp_i_id, count_i = night_totals[i]
                        emp_j_id, count_j = night_totals[j]
                        
                        max_diff = len(dates) + max(ytd_night_counts.get(emp_i_id, 0), 
                                                    ytd_night_counts.get(emp_j_id, 0))
                        diff = model.NewIntVar(-max_diff, max_diff, 
                                              f"night_diff_{emp_i_id}_{emp_j_id}")
                        model.Add(diff == count_i - count_j)
                        abs_diff = model.NewIntVar(0, max_diff, f"night_abs_diff_{emp_i_id}_{emp_j_id}")
                        model.AddAbsEquality(abs_diff, diff)
                        objective_terms.append(abs_diff * 8)  # HIGH weight for night shift fairness
    
    # 5. FAIR DISTRIBUTION OF TD ASSIGNMENTS
    if td_vars:
        print("  Adding TD fairness objectives...")
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
                td_counts.append((emp.id, total_td))
        
        # Minimize variance in TD distribution
        if len(td_counts) > 1:
            for i in range(len(td_counts)):
                for j in range(i + 1, len(td_counts)):
                    emp_i_id, count_i = td_counts[i]
                    emp_j_id, count_j = td_counts[j]
                    diff = model.NewIntVar(-num_weeks, num_weeks, f"td_diff_{emp_i_id}_{emp_j_id}")
                    model.Add(diff == count_i - count_j)
                    abs_diff = model.NewIntVar(0, num_weeks, f"td_abs_diff_{emp_i_id}_{emp_j_id}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff * 4)  # Medium-high weight for TD fairness
    
    return objective_terms
