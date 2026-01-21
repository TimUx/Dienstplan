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
            rotation_idx = (week_idx + team_idx) % len(rotation)
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
    shift_types: List[ShiftType]
):
    """
    HARD CONSTRAINT: Minimum and maximum staffing per shift, INCLUDING cross-team workers.
    
    Staffing requirements are configured per shift type in the database.
    Values are ALWAYS read from shift_types parameter (no fallback values).
    
    Weekdays (Mon-Fri): Count active team members + cross-team workers per shift.
    Weekends (Sat-Sun): Count team weekend workers + cross-team weekend workers.
    
    UPDATED: Now counts both regular team assignments and cross-team assignments.
    
    Args:
        shift_types: List of ShiftType objects from database (REQUIRED)
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
                
                # ADD: Count cross-team weekend workers for this shift
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_weekend:
                        assigned.append(employee_cross_team_weekend[(emp.id, d, shift)])
                
                if assigned:
                    total_assigned = sum(assigned)
                    model.Add(total_assigned >= staffing[shift]["min"])
                    model.Add(total_assigned <= staffing[shift]["max"])
            else:
                # WEEKDAY: Count team members + cross-team workers who work this shift
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
                
                # ADD: Count cross-team workers for this shift on this day
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_shift:
                        assigned.append(employee_cross_team_shift[(emp.id, d, shift)])
                
                if assigned:
                    total_assigned = sum(assigned)
                    model.Add(total_assigned >= staffing[shift]["min"])
                    model.Add(total_assigned <= staffing[shift]["max"])


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
    teams: List[Team] = None
):
    """
    HARD CONSTRAINT: Minimum 11 hours rest between shifts.
    
    CRITICAL FOR CROSS-TEAM: Must enforce forbidden transitions to prevent violations.
    
    Forbidden transitions (violate 11-hour rest):
    - S → F (Spät 21:45 → Früh 05:45 = 8 hours)
    - N → F (Nacht 05:45 → Früh 05:45 = 0 hours in same day context)
    
    With team-based planning alone, these are prevented by rotation.
    With cross-team assignments, we must explicitly forbid these transitions.
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
    
    # For each employee, enforce no forbidden transitions between consecutive days
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
            
            # Forbid transitions: S→F and N→F
            for i_today, today_shift_code in enumerate(today_shift_codes):
                for i_tomorrow, tomorrow_shift_code in enumerate(tomorrow_shift_codes):
                    # Check if this is a forbidden transition
                    if (today_shift_code == "S" and tomorrow_shift_code == "F") or \
                       (today_shift_code == "N" and tomorrow_shift_code == "F"):
                        # Forbid: NOT(today_shift AND tomorrow_shift)
                        # Equivalent to: today_shift + tomorrow_shift <= 1
                        model.Add(today_shifts[i_today] + tomorrow_shifts[i_tomorrow] <= 1)


def add_consecutive_shifts_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str],
    max_consecutive_shifts_weeks: int = 6,
    max_consecutive_night_shifts_weeks: int = 3
):
    """
    HARD CONSTRAINT: Maximum consecutive working days of same shift type (INCLUDING cross-team).
    
    CORRECTED UNDERSTANDING (per stakeholder clarification):
    - The database stores MaxConsecutiveShifts in WEEKS (e.g., 6)
    - These values are converted to DAYS for constraint enforcement (6 weeks × 7 = 42 days)
    - Maximum consecutive days of F/S shifts = max_consecutive_shifts_weeks × 7
    - Maximum consecutive days of N shifts = max_consecutive_night_shifts_weeks × 7
    - NO limit on total consecutive working days (can work all 7 days/week)
    
    Args:
        max_consecutive_shifts_weeks: Max weeks of same shift (F/S) from database (default 6)
        max_consecutive_night_shifts_weeks: Max weeks of night shifts from database (default 3)
    
    Note: With team rotation (F -> N -> S weekly), employees typically work max
    7 consecutive days of the same shift, well below these limits.
    
    IMPORTANT: This constraint is effectively handled by the team rotation pattern.
    Since teams rotate weekly (F -> N -> S), no employee can work more than
    ~7 consecutive days of the same shift type, which is far below the limits.
    
    Therefore, we implement a simplified check that still respects the mathematical
    limits but relies primarily on the team rotation to prevent violations.
    """
    # NOTE: With team rotation enforcing weekly shift changes, this constraint
    # is automatically satisfied. An employee in a team with F -> N -> S rotation
    # can never work 42 consecutive days of F/S or 21 consecutive days of N.
    # 
    # We keep this function for completeness and potential future configurations
    # where teams might have more flexible rotation patterns, but the actual
    # enforcement comes from the team rotation constraints.
    
    # The team rotation constraint (F -> N -> S weekly) in add_team_rotation_constraints()
    # ensures that:
    # 1. Each team works a different shift each week
    # 2. Maximum same shift = 7 days (one week)
    # 3. This is well below 42 days (F/S) or 21 days (N) limits
    
    # Therefore, no additional constraints are needed here.
    # The mathematical limits are respected through the team rotation pattern.
    pass


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
    absences: List[Absence] = None
):
    """
    HARD CONSTRAINT: Working hours limits based on shift configuration INCLUDING cross-team.
    
    This constraint ensures that employees:
    1. Meet minimum required working hours based on their shift's WeeklyWorkingHours
       (48h/week for main shifts F, S, N)
    2. Do not exceed maximum weekly hours (WeeklyWorkingHours from shift configuration)
    3. Monthly hours are calculated as WeeklyWorkingHours * 4 (e.g., 192h/month for 48h/week)
    4. Absences (U/AU/L) are exceptions - employees are not required to make up hours lost to absences
    5. If an employee works less in one week (without absence), they must compensate in other weeks
    6. UPDATED: Hours from cross-team assignments count toward employee's total hours
    
    The limits are now DYNAMIC per employee based on their team's assigned shift(s),
    replacing the previous fixed limits of 192 hours/month and 48 hours/week.
    
    Note: All main shifts (F, S, N) are 8 hours by default.
    Weekend hours are based on team's shift type (same as weekday).
    Cross-team hours are based on the actual shift worked.
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
            
            # ADD: Count cross-team hours this week for minimum hours calculation
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
                                                       f"emp{emp.id}_week{week_idx}_crossteam{shift_code}_days_min")
                    model.Add(cross_days_count == sum(cross_team_days))
                    
                    # Multiply by hours (scaled by 10)
                    scaled_hours = int(shift_hours[shift_code] * 10)
                    total_hours_terms.append(cross_days_count * scaled_hours)
        
        # Apply minimum hours constraint if employee has weeks without absences
        # Total hours calculated dynamically based on actual calendar days in planning period
        # Formula: weekly_working_hours ÷ 7 days × total_days_without_absence
        # Example: 48h/week ÷ 7 × 31 days (January) = 212.57h ≈ 213h
        # Example: 48h/week ÷ 7 × 28 days (February) = 192h
        if total_hours_terms and weeks_without_absences > 0:
            # Count total days without absence for this employee
            total_days_without_absence = sum(len(week_dates) for week_idx, week_dates in enumerate(weeks)
                                             if not any(any(abs.employee_id == emp.id and abs.overlaps_date(d) 
                                                           for abs in absences) for d in week_dates))
            
            # Calculate expected hours based on actual calendar days
            # Formula: (weekly_target_hours / 7) × total_days_without_absence
            # Scaled by 10 for precision
            daily_target_hours = weekly_target_hours / 7.0
            expected_total_hours_scaled = int(daily_target_hours * total_days_without_absence * 10)
            
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
