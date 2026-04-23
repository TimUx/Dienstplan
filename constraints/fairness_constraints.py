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


def add_fairness_objectives(
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
    
    return objective_terms
