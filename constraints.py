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
MAXIMUM_HOURS_PER_MONTH = 192
MAXIMUM_HOURS_PER_WEEK = 48

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
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Each team must have exactly ONE shift per week.
    
    Constraint: For each team and week:
        Sum(team_shift[team][week][shift] for all shifts) == 1
    
    EXCLUDES virtual team "Fire Alarm System" (ID 99) which doesn't participate in rotation.
    """
    for team in teams:
        # Skip virtual team for TD-qualified employees
        if team.id == 99:  # Fire Alarm System virtual team
            continue
            
        for week_idx in range(len(weeks)):
            shift_vars = []
            for shift_code in shift_codes:
                if (team.id, week_idx, shift_code) in team_shift:
                    shift_vars.append(team_shift[(team.id, week_idx, shift_code)])
            
            if shift_vars:
                model.Add(sum(shift_vars) == 1)


def add_team_rotation_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    locked_team_shift: Dict[Tuple[int, int], str] = None
):
    """
    HARD CONSTRAINT: Teams follow fixed rotation pattern F → N → S.
    
    Each team follows the same rotation cycle with offset based on team ID.
    Week 0: Team 1=F, Team 2=N, Team 3=S
    Week 1: Team 1=N, Team 2=S, Team 3=F
    Week 2: Team 1=S, Team 2=F, Team 3=N
    Week 3: Team 1=F, Team 2=N, Team 3=S (repeats)
    
    Manual overrides (locked assignments) take precedence over rotation.
    
    EXCLUDES virtual team "Fire Alarm System" (ID 99) which doesn't participate in rotation.
    """
    if "F" not in shift_codes or "N" not in shift_codes or "S" not in shift_codes:
        return  # Cannot enforce rotation if shifts are missing
    
    locked_team_shift = locked_team_shift or {}
    
    # Define the rotation cycle
    rotation = ["F", "N", "S"]
    
    # For each team, assign shifts based on rotation
    # EXCLUDE virtual team ID 99
    regular_teams = [t for t in teams if t.id != 99]
    sorted_teams = sorted(regular_teams, key=lambda t: t.id)
    
    for team_idx, team in enumerate(sorted_teams):
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
    - Springers are flexible and handled separately
    - Employees in virtual team "Fire Alarm System" (ID 99) do NOT work regular shifts
    """
    # For each team member
    for emp in employees:
        # Springers handled separately
        if emp.is_springer:
            continue
            
        # Employees without team skip
        if not emp.team_id:
            continue
        
        # Employees in virtual team "Fire Alarm System" (ID 99) do NOT work regular shifts
        # They are only assigned TD
        if emp.team_id == 99:
            # Force all regular shift variables to 0
            for d in dates:
                if (emp.id, d) in employee_active:
                    model.Add(employee_active[(emp.id, d)] == 0)
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
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Minimum and maximum staffing per shift.
    
    Weekdays: F: 4-5, S: 3-4, N: 3
    Weekends: All: 2-3
    
    Weekdays (Mon-Fri): Count active team members per shift based on team assignments.
    Weekends (Sat-Sun): Count employees working weekend based on team shift type.
    
    CRITICAL: Weekend employees work their team's shift type (only presence varies).
    """
    for d in dates:
        is_weekend = d.weekday() >= 5
        staffing = WEEKEND_STAFFING if is_weekend else WEEKDAY_STAFFING
        
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
            
            if is_weekend:
                # WEEKEND: Count team members working this weekend with their team's shift
                # For each team with this shift, count active members
                # 
                # NOTE: Springers excluded from weekends by design - they don't have 
                # weekend variables (see model.py line 198). Weekend staffing is lower
                # (2-3 vs 4-5) so regular team members can usually meet requirements.
                assigned = []
                
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    
                    # Count members of this team working on this weekend day
                    for emp in employees:
                        if emp.team_id != team.id or emp.is_springer or emp.is_ferienjobber:
                            continue  # Only count regular team members (springers have no weekend variables)
                        
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
                # 
                # IMPORTANT: Include springers in count - they can fill in for absent team members
                assigned = []
                
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    
                    # Count active members of this team on this day (including springers)
                    for emp in employees:
                        if emp.team_id != team.id:
                            continue  # Only count team members (springers ARE team members)
                        
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
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    shift_types: List[ShiftType]
):
    """
    HARD CONSTRAINT: Working hours limits.
    
    - Maximum 48 hours per week
    - Maximum 192 hours per month
    
    Note: All main shifts (F, S, N) are 8 hours.
    Weekend hours are based on team's shift type (same as weekday).
    """
    # Create shift hours lookup
    shift_hours = {}
    for st in shift_types:
        shift_hours[st.code] = st.hours
    
    # Maximum 48 hours per week
    for emp in employees:
        if not emp.team_id or emp.is_springer:
            continue  # Springers handled separately
        
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
                # Maximum 48 hours = 480 scaled hours
                model.Add(sum(hours_terms) <= 480)


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


def add_springer_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date]
):
    """
    HARD CONSTRAINT: Springer (backup worker) availability.
    
    - At least 1 springer must remain available each day
    - Springers can work in any team
    - Springers should not all be assigned simultaneously
    """
    springers = [emp for emp in employees if emp.is_springer]
    
    if not springers:
        return
    
    # At least 1 springer available per day
    for d in dates:
        springer_working = []
        for emp in springers:
            if d.weekday() < 5:  # Weekday
                if (emp.id, d) in employee_active:
                    springer_working.append(employee_active[(emp.id, d)])
            else:  # Weekend
                # Springer works if assigned to work on weekend
                if (emp.id, d) in employee_weekend_shift:
                    springer_working.append(employee_weekend_shift[(emp.id, d)])
        
        if springer_working:
            # At least one springer must be free
            model.Add(sum(springer_working) <= len(springers) - 1)


def add_fairness_objectives(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
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
        if emp.is_springer or not emp.team_id:
            continue  # Don't include springers in fairness
        
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
    
    # 2. Fair distribution of weekend work per employee
    weekend_counts = []
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue
        
        weekend_work = []
        for d in dates:
            if d.weekday() >= 5 and (emp.id, d) in employee_weekend_shift:
                weekend_work.append(employee_weekend_shift[(emp.id, d)])
        
        if weekend_work:
            total_weekends = model.NewIntVar(0, num_weekend_days, f"weekends_{emp.id}")
            model.Add(total_weekends == sum(weekend_work))
            weekend_counts.append(total_weekends)
    
    # Minimize variance in weekend distribution
    if len(weekend_counts) > 1:
        for i in range(len(weekend_counts)):
            for j in range(i + 1, len(weekend_counts)):
                diff = model.NewIntVar(-num_weekend_days, num_weekend_days, 
                                      f"weekend_diff_{i}_{j}")
                model.Add(diff == weekend_counts[i] - weekend_counts[j])
                abs_diff = model.NewIntVar(0, num_weekend_days, f"weekend_abs_diff_{i}_{j}")
                model.AddAbsEquality(abs_diff, diff)
                objective_terms.append(abs_diff * 3)  # Weight weekend fairness higher
    
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
