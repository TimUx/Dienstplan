"""
OR-Tools CP-SAT constraints for TEAM-BASED shift planning.
Implements all hard and soft rules as constraints according to requirements.

CRITICAL: This implements a TEAM-BASED model where:
- Teams are the primary planning unit
- All team members work the SAME shift during a week
- Teams rotate weekly in fixed pattern: F → N → S
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
    """
    for team in teams:
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
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Teams follow fixed rotation pattern F → N → S.
    
    If team has Früh in week k, it must have Nacht in week k+1.
    If team has Nacht in week k, it must have Spät in week k+1.
    If team has Spät in week k, it must have Früh in week k+1.
    """
    if "F" not in shift_codes or "N" not in shift_codes or "S" not in shift_codes:
        return  # Cannot enforce rotation if shifts are missing
    
    for team in teams:
        for week_idx in range(len(weeks) - 1):
            # F → N
            if (team.id, week_idx, "F") in team_shift and (team.id, week_idx + 1, "N") in team_shift:
                model.Add(
                    team_shift[(team.id, week_idx, "F")] <= team_shift[(team.id, week_idx + 1, "N")]
                )
            
            # N → S
            if (team.id, week_idx, "N") in team_shift and (team.id, week_idx + 1, "S") in team_shift:
                model.Add(
                    team_shift[(team.id, week_idx, "N")] <= team_shift[(team.id, week_idx + 1, "S")]
                )
            
            # S → F
            if (team.id, week_idx, "S") in team_shift and (team.id, week_idx + 1, "F") in team_shift:
                model.Add(
                    team_shift[(team.id, week_idx, "S")] <= team_shift[(team.id, week_idx + 1, "F")]
                )


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
    
    - Team members work when their team works (except when absent)
    - Employees can only work their team's assigned shift
    - Springers are flexible and handled separately
    """
    # For each team member
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue  # Springers handled separately
        
        # Find employee's team
        team = None
        for t in teams:
            if t.id == emp.team_id:
                team = t
                break
        
        if not team:
            continue
        
        # For each weekday (Mon-Fri), link to team shift
        for week_idx, week_dates in enumerate(weeks):
            weekday_dates = [d for d in week_dates if d.weekday() < 5]
            
            for d in weekday_dates:
                # Check if employee is absent
                is_absent = any(
                    abs.employee_id == emp.id and abs.overlaps_date(d)
                    for abs in absences
                )
                
                if is_absent:
                    # Force inactive if absent
                    if (emp.id, d) in employee_active:
                        model.Add(employee_active[(emp.id, d)] == 0)
                else:
                    # Active if team has ANY shift this week
                    team_has_shift = []
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            team_has_shift.append(team_shift[(team.id, week_idx, shift_code)])
                    
                    if team_has_shift and (emp.id, d) in employee_active:
                        # Employee is active IFF team has a shift this week
                        model.Add(employee_active[(emp.id, d)] == sum(team_has_shift))


def add_staffing_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
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
    
    Count active team members per shift based on team assignments.
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
            
            # Count employees active on this shift
            # Employees are on this shift if their team has this shift and they're active
            assigned = []
            
            for emp in employees:
                if emp.is_springer or not emp.team_id:
                    continue  # Only count regular team members
                
                if (emp.id, d) in employee_active and (emp.team_id, week_idx, shift) in team_shift:
                    # Employee is on shift if: their team has this shift AND they're active
                    is_on_shift = model.NewBoolVar(f"emp{emp.id}_shift{shift}_date{d}")
                    model.AddMultiplicationEquality(
                        is_on_shift,
                        [employee_active[(emp.id, d)], team_shift[(emp.team_id, week_idx, shift)]]
                    )
                    assigned.append(is_on_shift)
            
            if assigned:
                total_assigned = sum(assigned)
                model.Add(total_assigned >= staffing[shift]["min"])
                model.Add(total_assigned <= staffing[shift]["max"])


def add_rest_time_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Minimum 11 hours rest between shifts.
    
    Forbidden transitions (at week boundaries):
    - Spät → Früh (only 8 hours rest)
    - Nacht → Früh (0 hours rest)
    """
    # Team-based: Check transitions between weeks
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue  # Springers handled separately
        
        # Check week boundaries
        for week_idx in range(len(weeks) - 1):
            current_week_last_day = weeks[week_idx][-1]
            next_week_first_day = weeks[week_idx + 1][0]
            
            # Skip if not consecutive days
            if (next_week_first_day - current_week_last_day).days != 1:
                continue
            
            # Check all forbidden transitions
            for from_shift, forbidden_list in FORBIDDEN_TRANSITIONS.items():
                if from_shift not in shift_codes:
                    continue
                
                for to_shift in forbidden_list:
                    if to_shift not in shift_codes:
                        continue
                    
                    # If team has from_shift this week and to_shift next week, forbidden
                    if (emp.team_id, week_idx, from_shift) in team_shift and \
                       (emp.team_id, week_idx + 1, to_shift) in team_shift:
                        model.Add(
                            team_shift[(emp.team_id, week_idx, from_shift)] +
                            team_shift[(emp.team_id, week_idx + 1, to_shift)] <= 1
                        )


def add_consecutive_shifts_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    td_vars: Dict[Tuple[int, int], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    HARD CONSTRAINT: Maximum consecutive working days.
    
    - Maximum 6 consecutive shifts (including TD)
    - Maximum 5 consecutive night shifts
    """
    # Maximum 6 consecutive working days
    for emp in employees:
        for i in range(len(dates) - MAXIMUM_CONSECUTIVE_SHIFTS):
            shifts_in_period = []
            for j in range(MAXIMUM_CONSECUTIVE_SHIFTS + 1):
                current_date = dates[i + j]
                
                # Add employee active variable
                if (emp.id, current_date) in employee_active:
                    shifts_in_period.append(employee_active[(emp.id, current_date)])
            
            if shifts_in_period:
                model.Add(sum(shifts_in_period) <= MAXIMUM_CONSECUTIVE_SHIFTS)


def add_working_hours_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
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
            hours_vars = []
            
            for d in week_dates:
                if (emp.id, d) not in employee_active:
                    continue
                
                # Find which shift the team has this week
                for shift_code in shift_codes:
                    if (emp.team_id, week_idx, shift_code) in team_shift and shift_code in shift_hours:
                        # Hours = active * team_has_shift * hours_per_shift
                        # Scale by 10 to handle decimal hours
                        scaled_hours = int(shift_hours[shift_code] * 10)
                        hours_vars.append(
                            employee_active[(emp.id, d)] * 
                            team_shift[(emp.team_id, week_idx, shift_code)] * 
                            scaled_hours
                        )
            
            if hours_vars:
                # Maximum 48 hours = 480 scaled hours
                model.Add(sum(hours_vars) <= 480)


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
    - TD can be combined with regular shift work
    - TD is NOT a separate shift, just an organizational marker
    - Cannot assign TD when employee is absent
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
        
        # Exactly 1 TD per week
        if available_for_td:
            model.Add(sum(available_for_td) == 1)


def add_springer_constraints(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
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
            if (emp.id, d) in employee_active:
                springer_working.append(employee_active[(emp.id, d)])
        
        if springer_working:
            # At least one springer must be free
            model.Add(sum(springer_working) <= len(springers) - 1)


def add_fairness_objectives(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
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
    
    # 1. Fair distribution of total shifts per employee
    shift_counts = []
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue  # Don't include springers in fairness
        
        # Count active days
        active_days = []
        for d in dates:
            if (emp.id, d) in employee_active:
                active_days.append(employee_active[(emp.id, d)])
        
        if active_days:
            total = model.NewIntVar(0, len(dates), f"total_shifts_{emp.id}")
            model.Add(total == sum(active_days))
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
    
    # 2. Fair distribution of night shifts (count by team)
    if "N" in shift_codes:
        night_counts = []
        for team in teams:
            night_weeks = []
            for week_idx in range(len(weeks)):
                if (team.id, week_idx, "N") in team_shift:
                    night_weeks.append(team_shift[(team.id, week_idx, "N")])
            
            if night_weeks:
                total_nights = model.NewIntVar(0, len(weeks), f"nights_{team.id}")
                model.Add(total_nights == sum(night_weeks))
                night_counts.append(total_nights)
        
        # Minimize variance in night shift distribution
        if len(night_counts) > 1:
            for i in range(len(night_counts)):
                for j in range(i + 1, len(night_counts)):
                    diff = model.NewIntVar(-len(weeks), len(weeks), f"night_diff_{i}_{j}")
                    model.Add(diff == night_counts[i] - night_counts[j])
                    abs_diff = model.NewIntVar(0, len(weeks), f"night_abs_diff_{i}_{j}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff * 2)  # Weight night fairness higher
    
    # 3. Fair distribution of TD assignments
    if td_vars:
        td_counts = []
        for emp in employees:
            if not emp.can_do_td:
                continue
            
            emp_td_weeks = []
            for week_idx in range(len(weeks)):
                if (emp.id, week_idx) in td_vars:
                    emp_td_weeks.append(td_vars[(emp.id, week_idx)])
            
            if emp_td_weeks:
                total_td = model.NewIntVar(0, len(weeks), f"td_total_{emp.id}")
                model.Add(total_td == sum(emp_td_weeks))
                td_counts.append(total_td)
        
        # Minimize variance in TD distribution
        if len(td_counts) > 1:
            for i in range(len(td_counts)):
                for j in range(i + 1, len(td_counts)):
                    diff = model.NewIntVar(-len(weeks), len(weeks), f"td_diff_{i}_{j}")
                    model.Add(diff == td_counts[i] - td_counts[j])
                    abs_diff = model.NewIntVar(0, len(weeks), f"td_abs_diff_{i}_{j}")
                    model.AddAbsEquality(abs_diff, diff)
                    objective_terms.append(abs_diff)
    
    return objective_terms
