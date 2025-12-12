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
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str]
):
    """
    Add maximum consecutive shifts constraints.
    
    - Maximum 6 consecutive working days
    - Maximum 5 consecutive night shifts
    """
    
    # Maximum 6 consecutive working days
    for emp in employees:
        for i in range(len(dates) - MAXIMUM_CONSECUTIVE_SHIFTS):
            # Sum of all shifts in next 7 days
            shifts_in_period = []
            for j in range(MAXIMUM_CONSECUTIVE_SHIFTS + 1):
                for s in shift_codes:
                    if (emp.id, dates[i + j], s) in x:
                        shifts_in_period.append(x[(emp.id, dates[i + j], s)])
            
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
    employees: List[Employee],
    dates: List[date],
    shift_codes: List[str],
    shift_types: List[ShiftType]
):
    """
    Add working hours constraints.
    
    - Maximum 48 hours per week
    - Maximum 192 hours per month
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
            # Sum hours for this week
            hours_vars = []
            for d in week_dates:
                for s in shift_codes:
                    if (emp.id, d, s) in x and s in shift_hours:
                        # Multiply boolean var by shift hours
                        hours_vars.append(x[(emp.id, d, s)] * int(shift_hours[s]))
            
            if hours_vars:
                model.Add(sum(hours_vars) <= MAXIMUM_HOURS_PER_WEEK)
    
    # Maximum 192 hours per month (approximate as 30 days)
    for emp in employees:
        if len(dates) >= 30:
            # For each 30-day window
            for i in range(len(dates) - 29):
                month_dates = dates[i:i + 30]
                hours_vars = []
                for d in month_dates:
                    for s in shift_codes:
                        if (emp.id, d, s) in x and s in shift_hours:
                            hours_vars.append(x[(emp.id, d, s)] * int(shift_hours[s]))
                
                if hours_vars:
                    model.Add(sum(hours_vars) <= MAXIMUM_HOURS_PER_MONTH)


def add_special_function_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, date, str], cp_model.IntVar],
    bmt_vars: Dict[Tuple[int, date], cp_model.IntVar],
    bsb_vars: Dict[Tuple[int, date], cp_model.IntVar],
    employees: List[Employee],
    dates: List[date]
):
    """
    Add constraints for special functions (BMT, BSB).
    
    - Exactly 1 BMT per weekday (Mon-Fri)
    - Exactly 1 BSB per weekday (Mon-Fri)
    - Only qualified employees can be assigned
    - Employee cannot have regular shift and special function on same day
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
            bmt_assigned = [bmt_vars[(emp.id, d)] for emp in bmt_qualified if (emp.id, d) in bmt_vars]
            if bmt_assigned:
                model.Add(sum(bmt_assigned) == 1)
        
        # Exactly 1 BSB per weekday
        if bsb_qualified:
            bsb_assigned = [bsb_vars[(emp.id, d)] for emp in bsb_qualified if (emp.id, d) in bsb_vars]
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
    
    # Add to objective: minimize deviation from average
    if len(shift_counts) > 1:
        avg_shifts = sum([sc for sc in shift_counts]) // len(shift_counts)
        for sc in shift_counts:
            deviation = model.NewIntVar(-len(dates), len(dates), f"deviation_{sc.Name()}")
            model.Add(deviation == sc - avg_shifts)
            abs_deviation = model.NewIntVar(0, len(dates), f"abs_dev_{sc.Name()}")
            model.AddAbsEquality(abs_deviation, deviation)
            objective_terms.append(abs_deviation)
    
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
    
    return objective_terms
