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
    violation_tracker=None,
    relax_min_staffing: bool = False
) -> Tuple[List[cp_model.IntVar], List[Tuple[cp_model.IntVar, date]], Dict[str, List[Tuple[cp_model.IntVar, date]]], List[cp_model.IntVar], List[cp_model.IntVar]]:
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
        relax_min_staffing: When True, minimum staffing is treated as a soft constraint
            with penalty variables instead of a hard constraint. The returned
            min_staffing_violations list will contain the penalty variables.
            When False (default), minimum staffing is a hard constraint.
        
    Returns:
        5-tuple of (weekday_overstaffing_penalties, weekend_overstaffing_penalties, 
                  weekday_understaffing_by_shift, team_priority_violations,
                  min_staffing_violations) where:
                  - weekend_overstaffing_penalties is a list of (penalty_var, date) tuples for temporal weighting
                  - weekday_understaffing_by_shift is a dict mapping shift codes to lists of (penalty_var, date) tuples
                  - team_priority_violations are penalties for using cross-team when team has capacity
                  - min_staffing_violations is a list of IntVar penalty variables representing how far below
                    minimum staffing each shift/day falls (non-empty only when relax_min_staffing=True)
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
    
    shift_type_by_code = {st.code: st for st in shift_types}
    date_to_week_idx: Dict[date, int] = {}
    for w_idx, week_dates in enumerate(weeks):
        for wd in week_dates:
            date_to_week_idx[wd] = w_idx
    team_members: Dict[int, List[Employee]] = {}
    for emp in employees:
        if emp.team_id is not None:
            team_members.setdefault(emp.team_id, []).append(emp)

    # Initialize separate lists for different penalty types
    weekday_overstaffing_penalties = []
    weekend_overstaffing_penalties = []
    weekday_understaffing_by_shift = {shift: [] for shift in shift_codes}  # Separate by shift type for priority
    team_priority_violations = []  # Penalties for using cross-team when team has capacity
    min_staffing_violations = []  # Only populated when relax_min_staffing=True
    
    for d in dates:
        is_weekend = d.weekday() >= 5
        staffing = staffing_weekend if is_weekend else staffing_weekday
        
        week_idx = date_to_week_idx.get(d)
        if week_idx is None:
            continue
        
        for shift in shift_codes:
            if shift not in staffing:
                continue
            
            # Check if this shift works on this day (Mon-Fri vs Sat-Sun)
            # Find the shift type for this shift code
            shift_type = shift_type_by_code.get(shift)
            
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
                    for emp in team_members.get(team.id, []):
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
                    # Minimum staffing: HARD by default, SOFT when relax_min_staffing=True
                    min_required = staffing[shift]["min"]
                    if relax_min_staffing:
                        # Soft constraint: penalise shortfall instead of forbidding it
                        viol = model.NewIntVar(0, min_required, f"min_staff_viol_{shift}_{d}_weekend")
                        model.Add(viol >= min_required - total_assigned)
                        model.Add(viol >= 0)
                        min_staffing_violations.append(viol)
                    else:
                        model.Add(total_assigned >= min_required)
                    # HARD maximum staffing on weekends: enforce configured max strictly
                    model.Add(total_assigned <= staffing[shift]["max"])
                    
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
                    for emp in team_members.get(team.id, []):
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
                    # Minimum staffing: HARD by default, SOFT when relax_min_staffing=True
                    min_required = staffing[shift]["min"]
                    if relax_min_staffing:
                        viol = model.NewIntVar(0, min_required, f"min_staff_viol_{shift}_{d}_weekday")
                        model.Add(viol >= min_required - total_assigned)
                        model.Add(viol >= 0)
                        min_staffing_violations.append(viol)
                    else:
                        model.Add(total_assigned >= min_required)
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
    
    return weekday_overstaffing_penalties, weekend_overstaffing_penalties, weekday_understaffing_by_shift, team_priority_violations, min_staffing_violations


def add_total_weekend_staffing_limit(
    model: cp_model.CpModel,
    employee_active: Dict[Tuple[int, date], cp_model.IntVar],
    employee_weekend_shift: Dict[Tuple[int, date], cp_model.IntVar],
    employee_cross_team_shift: Dict[Tuple[int, date, str], cp_model.IntVar],
    employee_cross_team_weekend: Dict[Tuple[int, date, str], cp_model.IntVar],
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    employees: List[Employee],
    teams: List[Team],
    dates: List[date],
    weeks: List[List[date]],
    shift_codes: List[str],
    max_total_weekend_staff: int = 12
) -> List[Tuple[cp_model.IntVar, date]]:
    """
    SOFT CONSTRAINT: Limit total number of employees working on weekends across ALL shifts.
    
    While individual shifts have their own MaxStaffWeekend limits, this constraint
    addresses the requirement that the TOTAL number of employees on any weekend day
    should not exceed a certain limit (default 12).
    
    This is important because with 3 shifts (F, S, N) each having MaxStaffWeekend=5,
    the theoretical maximum is 15 employees on a weekend day, which is too many.
    
    According to requirements: "Ein Maximum von 12 Mitarbeitern an Wochenenden sollte 
    nicht überschritten werden. Dies sollte als Soft Kriterium mit erhöhter Priorität 
    umgesetzt werden."
    
    Translation: "A maximum of 12 employees on weekends should not be exceeded. 
    This should be implemented as a soft criterion with increased priority."
    
    This creates a penalty for each employee beyond the max_total_weekend_staff limit.
    The penalty should be higher than HOURS_SHORTAGE (100) to ensure it's prioritized.
    
    Args:
        max_total_weekend_staff: Maximum total employees allowed on weekend days (default 12)
        
    Returns:
        List of (penalty_var, date) tuples for total weekend overstaffing
    """
    total_weekend_overstaffing_penalties = []
    
    for d in dates:
        # Only apply to weekends (Saturday=5, Sunday=6)
        if d.weekday() < 5:
            continue
        
        # Find which week this date belongs to
        week_idx = None
        for w_idx, week_dates in enumerate(weeks):
            if d in week_dates:
                week_idx = w_idx
                break
        
        if week_idx is None:
            continue
        
        # Count ALL employees working on this weekend day across all shifts
        all_weekend_workers = []
        
        # Count team members working on weekend
        for team in teams:
            for shift in shift_codes:
                if (team.id, week_idx, shift) not in team_shift:
                    continue
                
                # Count members of this team working on this weekend day
                for emp in employees:
                    if emp.team_id != team.id:
                        continue
                    
                    if (emp.id, d) not in employee_weekend_shift:
                        continue
                    
                    # This employee works if: team has this shift AND employee is working weekend
                    is_working = model.NewBoolVar(f"total_weekend_{emp.id}_{d}_{shift}")
                    model.AddMultiplicationEquality(
                        is_working,
                        [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift)]]
                    )
                    all_weekend_workers.append(is_working)
        
        # Add cross-team weekend workers
        for emp in employees:
            for shift in shift_codes:
                if (emp.id, d, shift) in employee_cross_team_weekend:
                    all_weekend_workers.append(employee_cross_team_weekend[(emp.id, d, shift)])
        
        if all_weekend_workers:
            total_working = sum(all_weekend_workers)
            
            # Create penalty variable for exceeding total limit
            # Upper bound calculation: If we have N employees and max is M, worst case is (N - M) overstaffing
            # With typical setup of ~15 employees and max=12, this gives upper bound of 3-5
            # We use 20 as a safe upper bound to handle larger employee counts
            overstaffing = model.NewIntVar(0, 20, f"total_weekend_overstaff_{d}")
            model.Add(overstaffing >= total_working - max_total_weekend_staff)
            model.Add(overstaffing >= 0)
            
            total_weekend_overstaffing_penalties.append((overstaffing, d))
    
    return total_weekend_overstaffing_penalties


def add_cross_shift_capacity_enforcement(
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
) -> List[cp_model.IntVar]:
    """
    SOFT CONSTRAINT: Prevent overstaffing lower-capacity shifts when higher-capacity shifts have space.
    
    According to requirements: "Solange in den anderen Schichten laut Maximale Mitarbeiter Option 
    noch Plätze frei sind, soll die Maximale Grenze der N Schicht nicht überschritten werden."
    
    Translation: "As long as there are still free slots in other shifts according to the maximum 
    employee option, the maximum limit of the N shift should not be exceeded."
    
    This constraint adds a VERY HIGH penalty when:
    - Shift A (with lower max_staff) is overstaffed
    - AND Shift B (with higher max_staff) has unfilled capacity
    
    The penalty must be higher than HOURS_SHORTAGE (100) to ensure employees are assigned
    to higher-capacity shifts first before overstaffing lower-capacity shifts.
    
    Example with F(max=8), S(max=6), N(max=3):
    - If N has 4 workers (overstaffed by 1) and F has 7 workers (1 slot free), 
      this creates a violation penalty
    - If N has 4 workers (overstaffed by 1) but F and S are both full, no penalty
    
    Args:
        shift_types: List of ShiftType objects from database (REQUIRED)
        
    Returns:
        List of penalty variables for cross-shift capacity violations
    """
    if not shift_types:
        raise ValueError("shift_types parameter is required")
    
    # Build staffing lookup from shift_types
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
    
    # Sort shifts by max_staff to determine capacity ordering
    shifts_by_capacity_weekday = sorted(
        [(code, staffing_weekday[code]["max"]) for code in shift_codes if code in staffing_weekday],
        key=lambda x: x[1],
        reverse=True  # Highest capacity first
    )
    
    shifts_by_capacity_weekend = sorted(
        [(code, staffing_weekend[code]["max"]) for code in shift_codes if code in staffing_weekend],
        key=lambda x: x[1],
        reverse=True
    )
    
    capacity_violation_penalties = []
    
    for d in dates:
        is_weekend = d.weekday() >= 5
        staffing = staffing_weekend if is_weekend else staffing_weekday
        shifts_by_capacity = shifts_by_capacity_weekend if is_weekend else shifts_by_capacity_weekday
        
        # Find which week this date belongs to
        week_idx = None
        for w_idx, week_dates in enumerate(weeks):
            if d in week_dates:
                week_idx = w_idx
                break
        
        if week_idx is None:
            continue
        
        # For each pair of shifts where shift_high has higher capacity than shift_low
        for i, (shift_low, max_low) in enumerate(shifts_by_capacity):
            for j in range(i):  # Only compare with shifts that have higher or equal capacity
                shift_high, max_high = shifts_by_capacity[j]
                
                if max_high <= max_low:
                    continue  # Only enforce when there's a clear capacity difference
                
                # Check if this shift works on this day
                shift_type_low = None
                shift_type_high = None
                for st in shift_types:
                    if st.code == shift_low:
                        shift_type_low = st
                    if st.code == shift_high:
                        shift_type_high = st
                
                # Skip if either shift doesn't work on this day
                if shift_type_low and not shift_type_low.works_on_date(d):
                    continue
                if shift_type_high and not shift_type_high.works_on_date(d):
                    continue
                
                # Count workers for shift_low
                assigned_low = []
                if is_weekend:
                    # Weekend counting
                    for team in teams:
                        if (team.id, week_idx, shift_low) not in team_shift:
                            continue
                        for emp in employees:
                            if emp.team_id != team.id:
                                continue
                            if (emp.id, d) not in employee_weekend_shift:
                                continue
                            is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift_low}_d{d}_check")
                            model.AddMultiplicationEquality(
                                is_on_shift,
                                [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift_low)]]
                            )
                            assigned_low.append(is_on_shift)
                    # Add cross-team weekend workers
                    for emp in employees:
                        if (emp.id, d, shift_low) in employee_cross_team_weekend:
                            assigned_low.append(employee_cross_team_weekend[(emp.id, d, shift_low)])
                else:
                    # Weekday counting
                    for team in teams:
                        if (team.id, week_idx, shift_low) not in team_shift:
                            continue
                        for emp in employees:
                            if emp.team_id != team.id:
                                continue
                            if (emp.id, d) not in employee_active:
                                continue
                            is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift_low}_d{d}_check")
                            model.AddMultiplicationEquality(
                                is_on_shift,
                                [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift_low)]]
                            )
                            assigned_low.append(is_on_shift)
                    # Add cross-team workers
                    for emp in employees:
                        if (emp.id, d, shift_low) in employee_cross_team_shift:
                            assigned_low.append(employee_cross_team_shift[(emp.id, d, shift_low)])
                
                # Count workers for shift_high
                assigned_high = []
                if is_weekend:
                    # Weekend counting
                    for team in teams:
                        if (team.id, week_idx, shift_high) not in team_shift:
                            continue
                        for emp in employees:
                            if emp.team_id != team.id:
                                continue
                            if (emp.id, d) not in employee_weekend_shift:
                                continue
                            is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift_high}_d{d}_check")
                            model.AddMultiplicationEquality(
                                is_on_shift,
                                [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift_high)]]
                            )
                            assigned_high.append(is_on_shift)
                    # Add cross-team weekend workers
                    for emp in employees:
                        if (emp.id, d, shift_high) in employee_cross_team_weekend:
                            assigned_high.append(employee_cross_team_weekend[(emp.id, d, shift_high)])
                else:
                    # Weekday counting
                    for team in teams:
                        if (team.id, week_idx, shift_high) not in team_shift:
                            continue
                        for emp in employees:
                            if emp.team_id != team.id:
                                continue
                            if (emp.id, d) not in employee_active:
                                continue
                            is_on_shift = model.NewBoolVar(f"emp{emp.id}_onshift{shift_high}_d{d}_check")
                            model.AddMultiplicationEquality(
                                is_on_shift,
                                [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift_high)]]
                            )
                            assigned_high.append(is_on_shift)
                    # Add cross-team workers
                    for emp in employees:
                        if (emp.id, d, shift_high) in employee_cross_team_shift:
                            assigned_high.append(employee_cross_team_shift[(emp.id, d, shift_high)])
                
                if not assigned_low or not assigned_high:
                    continue
                
                # Calculate overstaffing in shift_low
                count_low = model.NewIntVar(0, 20, f"count_{shift_low}_{d}_capacity_check")
                model.Add(count_low == sum(assigned_low))
                overstaffing_low = model.NewIntVar(0, 20, f"overstaff_{shift_low}_{d}_capacity_check")
                model.Add(overstaffing_low >= count_low - staffing[shift_low]["max"])
                model.Add(overstaffing_low >= 0)
                
                # Calculate understaffing in shift_high
                count_high = model.NewIntVar(0, 20, f"count_{shift_high}_{d}_capacity_check")
                model.Add(count_high == sum(assigned_high))
                understaffing_high = model.NewIntVar(0, 20, f"understaff_{shift_high}_{d}_capacity_check")
                model.Add(understaffing_high >= staffing[shift_high]["max"] - count_high)
                model.Add(understaffing_high >= 0)
                
                # Violation = min(overstaffing_low, understaffing_high)
                # This is the number of workers in shift_low that could have been in shift_high
                violation = model.NewIntVar(0, 20, f"capacity_violation_{shift_low}_vs_{shift_high}_{d}")
                model.AddMinEquality(violation, [overstaffing_low, understaffing_high])
                capacity_violation_penalties.append(violation)
    
    return capacity_violation_penalties


def add_daily_shift_ratio_constraints(
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
) -> List[cp_model.IntVar]:
    """
    SOFT CONSTRAINT: Ensure shifts are staffed proportionally to their max_staff capacity on all days.
    
    This constraint enforces the capacity ordering from max_staff settings on a per-day basis.
    For example, with F(max=8), S(max=6), N(max=3), we want F >= S >= N on each day.
    
    Implementation: On each day, count workers in each shift type.
    For each pair of shifts where shift_a has higher max_staff than shift_b,
    create a violation variable when shift_b > shift_a, with a penalty.
    
    The penalty is high enough to matter but lower than critical operational constraints:
    - Lower than HOURS_SHORTAGE (100)
    - Lower than major operational constraints (200-20000)
    - Higher than TEAM_PRIORITY (50) to ensure it's respected
    - Much higher than understaffing weights (22-45)
    
    Penalty weight: 200 (above HOURS_SHORTAGE=100, below operational constraints)
    
    Args:
        shift_types: List of ShiftType objects from database
        
    Returns:
        List of penalty variables for ratio violations (to be minimized in objective)
    """
    if not shift_types:
        raise ValueError("shift_types parameter is required")
    
    # Build mapping from shift code to max_staff for weekdays and weekends
    shift_max_staff_weekday = {}
    shift_max_staff_weekend = {}
    for st in shift_types:
        if st.code in shift_codes:
            shift_max_staff_weekday[st.code] = st.max_staff_weekday
            shift_max_staff_weekend[st.code] = st.max_staff_weekend
    
    # Need at least 2 shifts to create ratio constraints
    if len(shift_max_staff_weekday) < 2 or len(shift_max_staff_weekend) < 2:
        return []
    
    # Weight for ratio violations - HIGH priority to ensure proper shift distribution
    # Set to 200 to prioritize shift ordering over hours shortage (100) but below
    # critical operational constraints (rest time 5000+, shift grouping 20000+)
    # This ensures shifts are distributed according to capacity while maintaining safety
    RATIO_VIOLATION_WEIGHT = 200
    
    ratio_violation_penalties = []
    
    for d in dates:
        # Determine if this is a weekend
        is_weekend = d.weekday() >= 5
        
        # Use appropriate max_staff values based on day type
        shift_max_staff = shift_max_staff_weekend if is_weekend else shift_max_staff_weekday
        
        # Sort shifts by max_staff (descending) to determine expected ordering
        sorted_shifts = sorted(shift_max_staff.items(), key=lambda x: x[1], reverse=True)
        
        # Find which week this date belongs to
        week_idx = None
        for w_idx, week_dates in enumerate(weeks):
            if d in week_dates:
                week_idx = w_idx
                break
        
        if week_idx is None:
            continue
        
        # Count workers for each shift type on this day
        shift_worker_counts = {}
        
        for shift_code in shift_max_staff.keys():
            if shift_code not in shift_codes:
                continue
            
            workers = []
            
            # Count team members assigned to this shift
            for team in teams:
                if (team.id, week_idx, shift_code) not in team_shift:
                    continue
                
                for emp in employees:
                    if emp.team_id != team.id:
                        continue
                    
                    # Use appropriate employee variable based on day type
                    if is_weekend:
                        if (emp.id, d) not in employee_weekend_shift:
                            continue
                        # Employee works this shift if team has shift AND employee is working weekend
                        is_on_shift = model.NewBoolVar(f"ratio_emp{emp.id}_onshift{shift_code}_date{d}")
                        model.AddMultiplicationEquality(
                            is_on_shift,
                            [employee_weekend_shift[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                        )
                        workers.append(is_on_shift)
                    else:
                        if (emp.id, d) not in employee_active:
                            continue
                        # Employee works this shift if team has shift AND employee is active
                        is_on_shift = model.NewBoolVar(f"ratio_emp{emp.id}_onshift{shift_code}_date{d}")
                        model.AddMultiplicationEquality(
                            is_on_shift,
                            [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift_code)]]
                        )
                        workers.append(is_on_shift)
            
            # Count cross-team workers (use appropriate variable based on day type)
            for emp in employees:
                if is_weekend:
                    if (emp.id, d, shift_code) in employee_cross_team_weekend:
                        workers.append(employee_cross_team_weekend[(emp.id, d, shift_code)])
                else:
                    if (emp.id, d, shift_code) in employee_cross_team_shift:
                        workers.append(employee_cross_team_shift[(emp.id, d, shift_code)])
            
            if workers:
                day_type = "weekend" if is_weekend else "weekday"
                count_var = model.NewIntVar(0, len(employees), f"{shift_code}_count_{d}_{day_type}")
                model.Add(count_var == sum(workers))
                shift_worker_counts[shift_code] = count_var
        
        # For each pair of shifts where shift_a should have more workers than shift_b,
        # create a penalty if shift_b > shift_a
        for i in range(len(sorted_shifts)):
            shift_a_code, shift_a_max = sorted_shifts[i]
            
            if shift_a_code not in shift_worker_counts:
                continue
            
            for j in range(i + 1, len(sorted_shifts)):
                shift_b_code, shift_b_max = sorted_shifts[j]
                
                if shift_b_code not in shift_worker_counts:
                    continue
                
                # shift_a has higher max_staff than shift_b, so we want shift_a >= shift_b
                # Create violation = max(0, shift_b - shift_a)
                violation = model.NewIntVar(0, len(employees), f"ratio_violation_{shift_a_code}_vs_{shift_b_code}_{d}")
                model.Add(violation >= shift_worker_counts[shift_b_code] - shift_worker_counts[shift_a_code])
                model.Add(violation >= 0)
                
                # Create weighted penalty variable
                penalty = model.NewIntVar(0, len(employees) * RATIO_VIOLATION_WEIGHT, f"ratio_penalty_{shift_a_code}_vs_{shift_b_code}_{d}")
                model.Add(penalty == violation * RATIO_VIOLATION_WEIGHT)
                
                ratio_violation_penalties.append(penalty)
    
    return ratio_violation_penalties


