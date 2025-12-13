"""
OR-Tools CP-SAT constraints for shift planning.
Implements all hard and soft rules as constraints.
"""

from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Set, Tuple
from entities import Employee, Absence, ShiftType, get_shift_type_by_id


# Shift planning rules (from .NET ShiftRules.cs)
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

# Ideal rotation pattern
IDEAL_ROTATION = ["F", "N", "S"]


def add_basic_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str],
    absences: List[Absence]
):
    """
    Add basic hard constraints that must always be satisfied.
    
    Constraints:
    - Only one shift per employee per day (or no shift)
    - Employees cannot work when absent
    """
    
    # Only one shift per employee per day
    for emp in employees:
        for d in dates:
            # Sum of all shifts for this employee on this day <= 1
            shift_vars = [x[(emp.id, d, s)] for s in shift_codes if (emp.id, d, s) in x]
            if shift_vars:
                model.Add(sum(shift_vars) <= 1)
    
    # Cannot work when absent
    for emp in employees:
        for d in dates:
            # Check if employee is absent on this date
            is_absent = any(
                abs.employee_id == emp.id and abs.overlaps_date(d)
                for abs in absences
            )
            
            if is_absent:
                # Force all shifts to 0 for this employee on this day
                for s in shift_codes:
                    if (emp.id, d, s) in x:
                        model.Add(x[(emp.id, d, s)] == 0)


def add_staffing_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add minimum and maximum staffing requirements per shift.
    
    Different requirements for weekdays vs weekends.
    """
    
    main_shifts = ["F", "S", "N"]
    
    for d in dates:
        is_weekend = d.weekday() >= 5  # Saturday or Sunday
        staffing = WEEKEND_STAFFING if is_weekend else WEEKDAY_STAFFING
        
        for shift in main_shifts:
            if shift not in shift_codes:
                continue
            
            # Sum all employees assigned to this shift on this day
            assigned = []
            for emp in employees:
                # Only count regular team members for staffing, not springers
                if not emp.is_springer and (emp.id, d, shift) in x:
                    assigned.append(x[(emp.id, d, shift)])
            
            if assigned:
                total_assigned = sum(assigned)
                
                # Minimum staffing
                model.Add(total_assigned >= staffing[shift]["min"])
                
                # Maximum staffing
                model.Add(total_assigned <= staffing[shift]["max"])


def add_rest_time_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add minimum rest time constraints (11 hours between shifts).
    
    This prevents forbidden transitions like:
    - Spät (ends 21:45) -> Früh (starts 05:45) = only 8 hours
    - Nacht (ends 05:45) -> Früh (starts 05:45) = 0 hours
    """
    
    for emp in employees:
        for i in range(len(dates) - 1):
            current_day = dates[i]
            next_day = dates[i + 1]
            
            # Check all forbidden transitions
            for from_shift, forbidden_list in FORBIDDEN_TRANSITIONS.items():
                if from_shift not in shift_codes:
                    continue
                
                for to_shift in forbidden_list:
                    if to_shift not in shift_codes:
                        continue
                    
                    # If employee works from_shift on current_day,
                    # they cannot work to_shift on next_day
                    if (emp.id, current_day, from_shift) in x and (emp.id, next_day, to_shift) in x:
                        model.Add(
                            x[(emp.id, current_day, from_shift)] + x[(emp.id, next_day, to_shift)] <= 1
                        )


def add_consecutive_shifts_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    bmt_vars: Dict[Tuple[int, date], cp_model.IntVar],
    bsb_vars: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add maximum consecutive shifts constraints.
    
    - Maximum 6 consecutive working days (including BMT/BSB assignments)
    - Maximum 5 consecutive night shifts
    """
    
    # Maximum 6 consecutive working days
    for emp in employees:
        for i in range(len(dates) - MAXIMUM_CONSECUTIVE_SHIFTS):
            # Sum of all shifts in next 7 days (including regular shifts AND special functions)
            shifts_in_period = []
            for j in range(MAXIMUM_CONSECUTIVE_SHIFTS + 1):
                current_date = dates[i + j]
                
                # Add regular shift variables
                for s in shift_codes:
                    if (emp.id, current_date, s) in x:
                        shifts_in_period.append(x[(emp.id, current_date, s)])
                
                # Add BMT variable if exists
                if (emp.id, current_date) in bmt_vars:
                    shifts_in_period.append(bmt_vars[(emp.id, current_date)])
                
                # Add BSB variable if exists
                if (emp.id, current_date) in bsb_vars:
                    shifts_in_period.append(bsb_vars[(emp.id, current_date)])
            
            if shifts_in_period:
                # At least one day off in every 7-day period
                model.Add(sum(shifts_in_period) <= MAXIMUM_CONSECUTIVE_SHIFTS)
    
    # Maximum 5 consecutive night shifts
    if "N" in shift_codes:
        for emp in employees:
            for i in range(len(dates) - MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS):
                night_shifts = []
                for j in range(MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS + 1):
                    if (emp.id, dates[i + j], "N") in x:
                        night_shifts.append(x[(emp.id, dates[i + j], "N")])
                
                if night_shifts:
                    model.Add(sum(night_shifts) <= MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS)


def add_working_hours_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    bmt_vars: Dict[Tuple[int, date], cp_model.IntVar],
    bsb_vars: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str],
    shift_types: List[ShiftType]
):
    """
    Add working hours constraints.
    
    - Maximum 48 hours per week (including BMT/BSB hours)
    - Maximum 192 hours per month (including BMT/BSB hours)
    """
    
    # Create shift hours lookup
    shift_hours = {}
    for st in shift_types:
        shift_hours[st.code] = st.hours
    
    # Maximum 48 hours per week
    # Group dates by week
    weeks = {}
    for d in dates:
        # Get Monday of the week
        monday = d - timedelta(days=d.weekday())
        if monday not in weeks:
            weeks[monday] = []
        weeks[monday].append(d)
    
    for emp in employees:
        for week_start, week_dates in weeks.items():
            # Sum hours for this week (use scaled integers to preserve precision)
            # Scale by 10 to handle 9.5 hours properly (e.g., 9.5 -> 95)
            hours_vars = []
            for d in week_dates:
                # Add regular shift hours
                for s in shift_codes:
                    if (emp.id, d, s) in x and s in shift_hours:
                        # Scale hours by 10: 8.0 -> 80, 9.5 -> 95
                        scaled_hours = int(shift_hours[s] * 10)
                        hours_vars.append(x[(emp.id, d, s)] * scaled_hours)
                
                # Add BMT hours (8 hours)
                if (emp.id, d) in bmt_vars:
                    hours_vars.append(bmt_vars[(emp.id, d)] * 80)  # 8.0 * 10
                
                # Add BSB hours (9.5 hours)
                if (emp.id, d) in bsb_vars:
                    hours_vars.append(bsb_vars[(emp.id, d)] * 95)  # 9.5 * 10
            
            if hours_vars:
                # Maximum 48 hours = 480 scaled hours
                model.Add(sum(hours_vars) <= 480)
    
    # Maximum 192 hours per month (approximate as 30 days)
    for emp in employees:
        if len(dates) >= 30:
            # For each 30-day window
            for i in range(len(dates) - 29):
                month_dates = dates[i:i + 30]
                hours_vars = []
                for d in month_dates:
                    # Add regular shift hours
                    for s in shift_codes:
                        if (emp.id, d, s) in x and s in shift_hours:
                            # Scale hours by 10: 8.0 -> 80, 9.5 -> 95
                            scaled_hours = int(shift_hours[s] * 10)
                            hours_vars.append(x[(emp.id, d, s)] * scaled_hours)
                    
                    # Add BMT hours (8 hours)
                    if (emp.id, d) in bmt_vars:
                        hours_vars.append(bmt_vars[(emp.id, d)] * 80)
                    
                    # Add BSB hours (9.5 hours)
                    if (emp.id, d) in bsb_vars:
                        hours_vars.append(bsb_vars[(emp.id, d)] * 95)
                
                if hours_vars:
                    # Maximum 192 hours = 1920 scaled hours
                    model.Add(sum(hours_vars) <= 1920)


def add_special_function_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    bmt_vars: Dict[Tuple[int, date], cp_model.IntVar],
    bsb_vars: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    absences: List[Absence]
):
    """
    Add constraints for special functions (BMT, BSB).
    
    - Exactly 1 BMT per weekday (Mon-Fri)
    - Exactly 1 BSB per weekday (Mon-Fri)
    - Only qualified employees can be assigned
    - Employee cannot have regular shift and special function on same day
    - Cannot assign when absent
    """
    
    # Get qualified employees
    bmt_qualified = [emp for emp in employees if emp.is_brandmeldetechniker]
    bsb_qualified = [emp for emp in employees if emp.is_brandschutzbeauftragter]
    
    for d in dates:
        is_weekday = d.weekday() < 5  # Monday to Friday
        
        if not is_weekday:
            continue
        
        # Exactly 1 BMT per weekday
        if bmt_qualified:
            bmt_assigned = []
            for emp in bmt_qualified:
                if (emp.id, d) in bmt_vars:
                    # Check if absent
                    is_absent = any(
                        abs.employee_id == emp.id and abs.overlaps_date(d)
                        for abs in absences
                    )
                    if not is_absent:
                        bmt_assigned.append(bmt_vars[(emp.id, d)])
            
            if bmt_assigned:
                model.Add(sum(bmt_assigned) == 1)
        
        # Exactly 1 BSB per weekday
        if bsb_qualified:
            bsb_assigned = []
            for emp in bsb_qualified:
                if (emp.id, d) in bsb_vars:
                    # Check if absent
                    is_absent = any(
                        abs.employee_id == emp.id and abs.overlaps_date(d)
                        for abs in absences
                    )
                    if not is_absent:
                        bsb_assigned.append(bsb_vars[(emp.id, d)])
            
            if bsb_assigned:
                model.Add(sum(bsb_assigned) == 1)
        
        # Cannot have both regular shift and special function
        for emp in employees:
            if emp.is_brandmeldetechniker and (emp.id, d) in bmt_vars:
                # If assigned BMT, cannot have any regular shift
                regular_shifts = [x[(emp.id, d, s)] for s in ["F", "S", "N"] if (emp.id, d, s) in x]
                if regular_shifts:
                    model.Add(bmt_vars[(emp.id, d)] + sum(regular_shifts) <= 1)
            
            if emp.is_brandschutzbeauftragter and (emp.id, d) in bsb_vars:
                # If assigned BSB, cannot have any regular shift
                regular_shifts = [x[(emp.id, d, s)] for s in ["F", "S", "N"] if (emp.id, d, s) in x]
                if regular_shifts:
                    model.Add(bsb_vars[(emp.id, d)] + sum(regular_shifts) <= 1)


def add_springer_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add constraints for Springer (backup workers).
    
    - At least 1 springer must remain available each day
    - Springers can work in any team
    """
    
    springers = [emp for emp in employees if emp.is_springer]
    
    if not springers:
        return
    
    # At least 1 springer available (not assigned) per day
    for d in dates:
        # Count springers assigned on this day
        springer_assigned = []
        for emp in springers:
            # Sum all shifts for this springer on this day
            shifts = [x[(emp.id, d, s)] for s in shift_codes if (emp.id, d, s) in x]
            if shifts:
                # Create indicator variable: 1 if springer works any shift
                is_working = model.NewBoolVar(f"springer_{emp.id}_working_{d}")
                model.Add(sum(shifts) >= 1).OnlyEnforceIf(is_working)
                model.Add(sum(shifts) == 0).OnlyEnforceIf(is_working.Not())
                springer_assigned.append(is_working)
        
        if springer_assigned:
            # At least one springer must be free (not working)
            model.Add(sum(springer_assigned) <= len(springers) - 1)


def add_fairness_objectives(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
) -> List[cp_model.IntVar]:
    """
    Add soft constraints for fairness (objectives to minimize/maximize).
    
    Returns list of variables to use in objective function.
    """
    
    objective_terms = []
    
    # 1. Minimize variance in total shifts per employee
    shift_counts = []
    for emp in employees:
        if emp.is_springer:
            continue  # Don't include springers in fairness calc
        
        shifts = [x[(emp.id, d, s)] for d in dates for s in shift_codes if (emp.id, d, s) in x]
        if shifts:
            total = model.NewIntVar(0, len(dates), f"total_shifts_{emp.id}")
            model.Add(total == sum(shifts))
            shift_counts.append(total)
    
    # Add to objective: minimize variance between employees
    # Instead of calculating average, minimize pairwise differences
    if len(shift_counts) > 1:
        for i in range(len(shift_counts)):
            for j in range(i + 1, len(shift_counts)):
                diff = model.NewIntVar(-len(dates), len(dates), f"diff_{i}_{j}")
                model.Add(diff == shift_counts[i] - shift_counts[j])
                abs_diff = model.NewIntVar(0, len(dates), f"abs_diff_{i}_{j}")
                model.AddAbsEquality(abs_diff, diff)
                objective_terms.append(abs_diff)
    
    # 2. Prefer ideal rotation (F -> N -> S)
    for emp in employees:
        for i in range(len(dates) - 1):
            # Check for ideal transitions
            if ("F" in shift_codes and "N" in shift_codes and 
                (emp.id, dates[i], "F") in x and (emp.id, dates[i + 1], "N") in x):
                # Reward F -> N transition
                good_transition = model.NewBoolVar(f"good_fn_{emp.id}_{i}")
                model.Add(x[(emp.id, dates[i], "F")] + x[(emp.id, dates[i + 1], "N")] == 2).OnlyEnforceIf(good_transition)
                objective_terms.append(good_transition * -10)  # Negative to maximize
            
            if ("N" in shift_codes and "S" in shift_codes and 
                (emp.id, dates[i], "N") in x and (emp.id, dates[i + 1], "S") in x):
                # Reward N -> S transition
                good_transition = model.NewBoolVar(f"good_ns_{emp.id}_{i}")
                model.Add(x[(emp.id, dates[i], "N")] + x[(emp.id, dates[i + 1], "S")] == 2).OnlyEnforceIf(good_transition)
                objective_terms.append(good_transition * -10)  # Negative to maximize
    
    # 3. Team-based scheduling: encourage teams to work same shifts in same week
    # Group employees by team
    team_employees = {}
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue
        if emp.team_id not in team_employees:
            team_employees[emp.team_id] = []
        team_employees[emp.team_id].append(emp)
    
    # Group dates by week
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # For each team and week, encourage members to work the same shift type
    for team_id, team_emps in team_employees.items():
        for week_idx, week_dates in enumerate(weeks):
            weekday_dates = [d for d in week_dates if d.weekday() < 5]
            if not weekday_dates:
                continue
            
            # For each shift type, count how many team members work it this week
            for shift in shift_codes:
                team_shift_vars = []
                for emp in team_emps:
                    for d in weekday_dates:
                        if (emp.id, d, shift) in x:
                            team_shift_vars.append(x[(emp.id, d, shift)])
                
                # Team cohesion is implicitly encouraged by:
                # 1. Staffing constraints requiring specific numbers per shift
                # 2. Team rotation constraints guiding assignments
                # 3. The fairness objective minimizing variance
                # No additional constraints needed here
    
    return objective_terms


def add_team_rotation_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add team-based rotation constraints for weekly shift planning.
    
    HARD CONSTRAINTS:
    - All team members work the SAME shift type during a given week
    - Shift assignment is weekly, not daily
    - Teams rotate weekly in pattern: Früh → Nacht → Spät
    
    Example:
    - Week 1: Team Alpha = F (all week), Team Beta = N (all week), Team Gamma = S (all week)
    - Week 2: Team Alpha = N (all week), Team Beta = S (all week), Team Gamma = F (all week)
    - Week 3: Team Alpha = S (all week), Team Beta = F (all week), Team Gamma = N (all week)
    """
    
    # Group employees by team (excluding springers and employees without team)
    team_employees = {}
    for emp in employees:
        if emp.is_springer or not emp.team_id:
            continue
        if emp.team_id not in team_employees:
            team_employees[emp.team_id] = []
        team_employees[emp.team_id].append(emp)
    
    # Only apply if we have at least 2 teams with members
    if len(team_employees) < 2:
        return
    
    # Group dates by week (Monday = start of week)
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:  # Monday and week has content
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Define rotation pattern: F → N → S
    shift_rotation = ["F", "N", "S"]
    
    # For each team and each week, enforce same shift for all team members
    for week_idx, week_dates in enumerate(weeks):
        # Only enforce on weekdays (Mon-Fri), weekends can be more flexible
        weekday_dates = [d for d in week_dates if d.weekday() < 5]
        
        if not weekday_dates:
            continue
        
        # Get sorted team IDs for consistent rotation
        team_ids = sorted(team_employees.keys())
        
        for team_idx, team_id in enumerate(team_ids):
            # Determine assigned shift for this team in this week
            # Rotation: (week_number + team_offset) % 3
            assigned_shift_idx = (week_idx + team_idx) % len(shift_rotation)
            assigned_shift = shift_rotation[assigned_shift_idx]
            
            if assigned_shift not in shift_codes:
                continue
            
            team_emps = team_employees[team_id]
            
            # HARD CONSTRAINT: Each team member can ONLY work their team's assigned shift
            # (or no shift due to absence, BMT/BSB, etc.)
            for emp in team_emps:
                for d in weekday_dates:
                    # For each shift type that is NOT the assigned shift
                    for other_shift in shift_codes:
                        if other_shift != assigned_shift:
                            # Team member cannot work other shifts this week
                            if (emp.id, d, other_shift) in x:
                                model.Add(x[(emp.id, d, other_shift)] == 0)
