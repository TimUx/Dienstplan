"""
Solver for the TEAM-BASED shift planning problem using OR-Tools CP-SAT.
Configures and runs the solver, returns solution.
"""

from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from entities import Employee, ShiftAssignment, STANDARD_SHIFT_TYPES, get_shift_type_by_id
from model import ShiftPlanningModel
from constraints import (
    add_team_shift_assignment_constraints,
    add_team_rotation_constraints,
    add_employee_team_linkage_constraints,
    add_staffing_constraints,
    add_rest_time_constraints,
    add_consecutive_shifts_constraints,
    add_working_hours_constraints,
    add_td_constraints,
    add_weekly_available_employee_constraint,
    add_fairness_objectives,
    add_weekly_shift_type_limit_constraints,
    add_weekend_shift_consistency_constraints,
    add_team_night_shift_consistency_constraints,
    add_shift_sequence_grouping_constraints,
    add_minimum_consecutive_weekday_shifts_constraints
)


class ShiftPlanningSolver:
    """
    Solver for the shift planning problem.
    """
    
    def __init__(
        self,
        planning_model: ShiftPlanningModel,
        time_limit_seconds: int = 300,
        num_workers: int = 8,
        global_settings: Dict = None
    ):
        """
        Initialize the solver.
        
        Args:
            planning_model: The shift planning model
            time_limit_seconds: Maximum time for solver (default 5 minutes)
            num_workers: Number of parallel workers for solver
            global_settings: Dict with global settings from database (optional)
                - max_consecutive_shifts_weeks: Max weeks of same shift (default 6)
                - max_consecutive_night_shifts_weeks: Max weeks of night shifts (default 3)
                - min_rest_hours: Min rest hours between shifts (default 11)
        """
        self.planning_model = planning_model
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self.solution = None
        self.status = None
        
        # Store global settings
        if global_settings is None:
            global_settings = {}
        self.max_consecutive_shifts_weeks = global_settings.get('max_consecutive_shifts_weeks', 6)
        self.max_consecutive_night_shifts_weeks = global_settings.get('max_consecutive_night_shifts_weeks', 3)
        self.min_rest_hours = global_settings.get('min_rest_hours', 11)
    
    def add_all_constraints(self):
        """
        Add all constraints to the TEAM-BASED model with CROSS-TEAM support.
        """
        model = self.planning_model.get_model()
        (team_shift, employee_active, employee_weekend_shift, 
         employee_cross_team_shift, employee_cross_team_weekend, td_vars) = self.planning_model.get_variables()
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_codes = self.planning_model.shift_codes
        absences = self.planning_model.absences
        shift_types = self.planning_model.shift_types
        
        # Get locked assignments
        locked_team_shift = self.planning_model.locked_team_shift
        
        print("Adding constraints...")
        
        # CORE TEAM-BASED CONSTRAINTS
        print("  - Team shift assignment (exactly one shift per team per week)")
        add_team_shift_assignment_constraints(model, team_shift, teams, weeks, shift_codes, shift_types)
        
        print("  - Team rotation (F → N → S pattern)")
        add_team_rotation_constraints(model, team_shift, teams, weeks, shift_codes, locked_team_shift, shift_types)
        
        print("  - Employee-team linkage (derive employee activity from team shifts)")
        add_employee_team_linkage_constraints(model, team_shift, employee_active, employee_cross_team_shift, employees, teams, dates, weeks, shift_codes, absences, employee_weekend_shift, employee_cross_team_weekend)
        
        # STAFFING AND WORKING CONDITIONS
        print("  - Staffing requirements (min hard / max soft, including cross-team)")
        # NEW: Collect separate penalties for weekday/weekend overstaffing and weekday understaffing by shift
        # Also collect team priority violations (cross-team usage when team has capacity)
        weekday_overstaffing, weekend_overstaffing, weekday_understaffing_by_shift, team_priority_violations = add_staffing_constraints(
            model, employee_active, employee_weekend_shift, team_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, 
            employees, teams, dates, weeks, shift_codes, shift_types)
        
        print("  - Rest time constraints (11h min, soft penalties for violations)")
        rest_violation_penalties = add_rest_time_constraints(model, employee_active, employee_weekend_shift, team_shift, 
                                 employee_cross_team_shift, employee_cross_team_weekend, 
                                 employees, dates, weeks, shift_codes, teams)
        
        # Shift stability constraint (prevent shift hopping)
        print("  - Shift stability constraints (prevent rapid shift changes like N→S→N)")
        from constraints import add_shift_stability_constraints
        shift_hopping_penalties = add_shift_stability_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Shift sequence grouping constraint (prevent isolated shift types)
        print("  - Shift sequence grouping constraints (prevent isolated shift types like S-S-F-S-S)")
        shift_grouping_penalties = add_shift_sequence_grouping_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Minimum consecutive weekday shifts constraint (enforce at least 2 consecutive days for same shift during weekdays)
        print("  - Minimum consecutive weekday shifts constraints (min 2 consecutive days for same shift Mon-Fri)")
        min_consecutive_weekday_penalties = add_minimum_consecutive_weekday_shifts_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Weekly shift type limit constraint (max 2 different shift types per week)
        print("  - Weekly shift type limit constraints (max 2 shift types per week)")
        weekly_shift_type_penalties = add_weekly_shift_type_limit_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes, max_shift_types_per_week=2)
        
        # Weekend shift consistency constraint (no shift type changes within weekends)
        print("  - Weekend shift consistency constraints (prevent shift changes Fri→Sat/Sun)")
        weekend_consistency_penalties = add_weekend_shift_consistency_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes)
        
        # Team night shift consistency constraint (discourage cross-team night shifts)
        print("  - Team night shift consistency constraints (night shifts stay in night shift teams)")
        night_team_consistency_penalties = add_team_night_shift_consistency_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes)
        
        # Consecutive shifts constraint (re-enabled as SOFT constraint per @TimUx)
        # Limits consecutive working days and consecutive night shifts
        # Violations are penalized but allowed for feasibility
        print("  - Consecutive shifts constraints (soft - max consecutive days)")
        consecutive_violation_penalties = add_consecutive_shifts_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend, 
            td_vars, employees, teams, dates, weeks, shift_codes,
            self.max_consecutive_shifts_weeks,  # Now interpreted as DAYS
            self.max_consecutive_night_shifts_weeks)  # Now interpreted as DAYS
        
        print("  - Working hours constraints (soft target only, no hard 192h minimum)")
        hours_shortage_objectives = add_working_hours_constraints(
            model, employee_active, employee_weekend_shift, team_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, 
            td_vars, employees, teams, dates, weeks, shift_codes, shift_types, absences)
        
        # BLOCK SCHEDULING FOR CROSS-TEAM
        print("  - Weekly block constraints (Mon-Fri blocks for cross-team assignments)")
        from constraints import add_weekly_block_constraints
        add_weekly_block_constraints(model, employee_active, employee_cross_team_shift, 
                                    employees, dates, weeks, shift_codes, absences)
        
        # BLOCK SCHEDULING FOR TEAM MEMBERS (FLEXIBLE)
        print("  - Team member block constraints (prevent isolated days, encourage full blocks)")
        from constraints import add_team_member_block_constraints
        block_objective_vars = add_team_member_block_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employees, teams, dates, weeks, shift_codes, absences)
        
        # SPECIAL FUNCTIONS
        print("  - TD constraints (Tagdienst = organizational marker)")
        add_td_constraints(model, employee_active, td_vars, employees, dates, weeks, absences)
        
        # DISABLED: Weekly available employee constraint - conflicts with configured weekly_working_hours requirement
        # The constraint forces at least 1 employee to have 0 working days per week,
        # which prevents employees from reaching their target hours (e.g., 48h/week = 6 days)
        # See WORKING_HOURS_FIX.md for full analysis
        # 
        # print("  - Weekly available employee constraint (at least 1 free per week)")
        # add_weekly_available_employee_constraint(model, employee_active, employee_weekend_shift, employees, teams, weeks)
        
        # SOFT CONSTRAINTS (OPTIMIZATION)
        print("  - Fairness objectives (per-employee, year-long, including block scheduling)")
        objective_terms = add_fairness_objectives(
            model, employee_active, employee_weekend_shift, team_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, 
            td_vars, employees, teams, dates, weeks, shift_codes,
            self.planning_model.ytd_weekend_counts,
            self.planning_model.ytd_night_counts,
            self.planning_model.ytd_holiday_counts
        )
        
        # Add block scheduling objectives (encourage full blocks)
        # These are bonuses, so we want to maximize them (minimize negative sum)
        if block_objective_vars:
            print(f"  Adding {len(block_objective_vars)} block scheduling bonus objectives...")
            for bonus_var in block_objective_vars:
                objective_terms.append(-bonus_var)  # Negative because we minimize
        
        # Add consecutive shifts violation penalties (discourage but allow for feasibility)
        if consecutive_violation_penalties:
            print(f"  Adding {len(consecutive_violation_penalties)} consecutive shifts violation penalties...")
            for penalty_var in consecutive_violation_penalties:
                objective_terms.append(penalty_var)  # Already weighted (300-400 per violation)
        
        # Add rest time violation penalties (strongly discourage but allow for feasibility)
        if rest_violation_penalties:
            print(f"  Adding {len(rest_violation_penalties)} rest time violation penalties...")
            for penalty_var in rest_violation_penalties:
                objective_terms.append(penalty_var)  # Already weighted (50 or 500 per violation)
        
        # Add shift hopping penalties (discourage rapid shift changes)
        if shift_hopping_penalties:
            print(f"  Adding {len(shift_hopping_penalties)} shift hopping penalties...")
            for penalty_var in shift_hopping_penalties:
                objective_terms.append(penalty_var)  # Already weighted (200 per hopping pattern)
        
        # Add shift grouping penalties (prevent isolated shift types)
        if shift_grouping_penalties:
            print(f"  Adding {len(shift_grouping_penalties)} shift grouping penalties...")
            for penalty_var in shift_grouping_penalties:
                objective_terms.append(penalty_var)  # Already weighted (1000 per isolation)
        
        # Add minimum consecutive weekday shifts penalties (strongly enforce min 2 consecutive days during weekdays)
        if min_consecutive_weekday_penalties:
            print(f"  Adding {len(min_consecutive_weekday_penalties)} minimum consecutive weekday shift penalties...")
            for penalty_var in min_consecutive_weekday_penalties:
                objective_terms.append(penalty_var)  # Already weighted (2000 per single-day violation)
        
        # Add weekly shift type limit penalties (strongly discourage > 2 shift types per week)
        if weekly_shift_type_penalties:
            print(f"  Adding {len(weekly_shift_type_penalties)} weekly shift type diversity penalties...")
            for penalty_var in weekly_shift_type_penalties:
                objective_terms.append(penalty_var)  # Already weighted (500 per violation)
        
        # Add weekend consistency penalties (discourage shift changes from Fri to Sat/Sun)
        if weekend_consistency_penalties:
            print(f"  Adding {len(weekend_consistency_penalties)} weekend consistency penalties...")
            for penalty_var in weekend_consistency_penalties:
                objective_terms.append(penalty_var)  # Already weighted (300 per mismatch)
        
        # Add team night shift consistency penalties (strongly discourage cross-team night shifts)
        if night_team_consistency_penalties:
            print(f"  Adding {len(night_team_consistency_penalties)} team night shift consistency penalties...")
            for penalty_var in night_team_consistency_penalties:
                objective_terms.append(penalty_var)  # Already weighted (600 per violation)
        
        # Add hours shortage objectives (minimize shortage from target hours)
        # These are shortages, so we want to minimize them directly
        if hours_shortage_objectives:
            print(f"  Adding {len(hours_shortage_objectives)} target hours shortage penalties...")
            for shortage_var in hours_shortage_objectives:
                objective_terms.append(shortage_var)  # Positive because we minimize shortage
        
        # Add overstaffing penalties with differential weights
        # CRITICAL: Weekend overstaffing should be HEAVILY penalized (weight 50x)
        # to prioritize filling weekday gaps before scheduling weekend shifts
        # Weekday overstaffing is less critical (weight 2x)
        if weekend_overstaffing:
            print(f"  Adding {len(weekend_overstaffing)} weekend overstaffing penalties (weight 50x)...")
            for overstaff_var in weekend_overstaffing:
                objective_terms.append(overstaff_var * 50)  # Very heavy penalty for weekend overstaffing
        
        if weekday_overstaffing:
            print(f"  Adding {len(weekday_overstaffing)} weekday overstaffing penalties (weight 2x)...")
            for overstaff_var in weekday_overstaffing:
                objective_terms.append(overstaff_var * 2)  # Light penalty for weekday overstaffing
        
        # Add weekday understaffing penalties with SHIFT-SPECIFIC PRIORITY weights
        # Priority order: Früh (F) > Spät (S) > Nacht (N)
        # Higher weight = higher priority to fill
        # Use VERY strong differentials to ensure priority overrides other soft constraints
        shift_priority_weights = {
            'F': 20,  # Früh/Early - highest priority (4x night)
            'S': 12,  # Spät/Late - medium priority (2.4x night)
            'N': 5    # Nacht/Night - lowest priority (baseline)
        }
        
        for shift_code, understaffing_list in weekday_understaffing_by_shift.items():
            if understaffing_list:
                weight = shift_priority_weights.get(shift_code, 5)  # Default to 5 if shift not in priority map
                shift_name = {'F': 'Früh', 'S': 'Spät', 'N': 'Nacht'}.get(shift_code, shift_code)
                print(f"  Adding {len(understaffing_list)} {shift_name} ({shift_code}) weekday understaffing penalties (weight {weight}x)...")
                for understaff_var in understaffing_list:
                    objective_terms.append(understaff_var * weight)
        
        # NEW: Add team priority violation penalties
        # Strongly penalize using cross-team workers when own team has unfilled capacity
        # Weight 10x to ensure team members are preferred over cross-team workers
        if team_priority_violations:
            print(f"  Adding {len(team_priority_violations)} team priority violation penalties (weight 10x)...")
            for violation_var in team_priority_violations:
                objective_terms.append(violation_var * 10)
        
        # NEW: Add shift type preference objective to directly reward F > S > N
        # Count total staff assigned to each shift and apply inverse priority weights
        # Lower priority shifts get small penalties to discourage their use when alternatives exist
        print("  Adding shift type preference objectives (F > S > N)...")
        shift_penalty_weights = {
            'F': -3,  # Früh/Early - REWARD (negative penalty = bonus)
            'S': 1,   # Spät/Late - slight penalty (less preferred than F)
            'N': 3    # Nacht/Night - stronger PENALTY (discourage when possible)
        }
        
        for d in dates:
            if d.weekday() >= 5:  # Skip weekends
                continue
                
            # Find which week this date belongs to
            week_idx = None
            for w_idx, week_dates in enumerate(weeks):
                if d in week_dates:
                    week_idx = w_idx
                    break
            
            if week_idx is None:
                continue
            
            for shift in shift_codes:
                if shift not in shift_penalty_weights:
                    continue
                    
                # Count employees working this shift on this day
                assigned = []
                
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    
                    # Count active members of this team on this day
                    for emp in employees:
                        if emp.team_id != team.id:
                            continue
                        
                        if (emp.id, d) not in employee_active:
                            continue
                        
                        # Employee works this shift if team has shift AND employee is active
                        is_on_shift = model.NewBoolVar(f"pref_emp{emp.id}_onshift{shift}_date{d}")
                        model.AddMultiplicationEquality(
                            is_on_shift,
                            [employee_active[(emp.id, d)], team_shift[(team.id, week_idx, shift)]]
                        )
                        assigned.append(is_on_shift)
                
                # Add cross-team workers for this shift on this day
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_shift:
                        assigned.append(employee_cross_team_shift[(emp.id, d, shift)])
                
                if assigned:
                    # Count total assigned to this shift
                    total_assigned = model.NewIntVar(0, len(employees), f"pref_total_{shift}_{d}")
                    model.Add(total_assigned == sum(assigned))
                    
                    # Apply priority weight (negative = reward, positive = penalty)
                    weight = shift_penalty_weights[shift]
                    objective_terms.append(total_assigned * weight)
        
        # Set objective function (minimize sum of objective terms)
        if objective_terms:
            model.Minimize(sum(objective_terms))
        
        print("All constraints added successfully!")
    
    def diagnose_infeasibility(self) -> Dict[str, any]:
        """
        Diagnose potential causes of infeasibility by analyzing the model configuration.
        
        Returns:
            Dictionary with diagnostic information about potential constraint violations
        """
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        absences = self.planning_model.absences
        shift_types = self.planning_model.shift_types
        shift_codes = self.planning_model.shift_codes
        weeks = self.planning_model.weeks
        
        diagnostics = {
            'total_employees': len(employees),
            'total_teams': len(teams),
            'planning_days': len(dates),
            'planning_weeks': len(dates) / 7.0,  # Actual weeks, not calendar weeks
            'total_absences': len(absences),
            'potential_issues': []
        }
        
        # Check absence impact - optimized to avoid O(absences × dates)
        # Build a set of (employee_id, date) tuples for all absences
        absent_employee_dates = set()
        for absence in absences:
            for d in dates:
                if absence.start_date <= d <= absence.end_date:
                    absent_employee_dates.add((absence.employee_id, d))
        
        # Count unique employees who have ANY absence during the planning period
        employees_with_absences = set(emp_id for emp_id, _ in absent_employee_dates)
        
        # Calculate average daily absence rate (more accurate than counting employees)
        total_employee_days = len(employees) * len(dates)
        absent_days = len(absent_employee_dates)
        absence_ratio = absent_days / total_employee_days if total_employee_days > 0 else 0
        
        # For display: count employees who are absent for a significant portion of the period
        # (more than 50% of days). Group by employee_id for better performance.
        employee_absence_counts = {}
        for emp_id, _ in absent_employee_dates:
            employee_absence_counts[emp_id] = employee_absence_counts.get(emp_id, 0) + 1
        
        significantly_absent = sum(1 for count in employee_absence_counts.values() if count > len(dates) / 2)
        
        diagnostics['total_employees'] = len(employees)  # All employees in the system
        diagnostics['employees_with_absences'] = len(employees_with_absences)
        diagnostics['significantly_absent_employees'] = significantly_absent
        diagnostics['total_absence_days'] = absent_days
        diagnostics['absence_ratio'] = absence_ratio
        
        # Deprecated: Keep for backward compatibility with existing code
        diagnostics['available_employees'] = len(employees)
        diagnostics['absent_employees'] = len(employees_with_absences)
        
        # Build staffing requirements from shift_types (database configuration)
        if not shift_types:
            raise ValueError("shift_types is required for diagnostics - must be loaded from database")
        
        staffing_weekday = {}
        for st in shift_types:
            if st.code in shift_codes:
                staffing_weekday[st.code] = {
                    "min": st.min_staff_weekday,
                    "max": st.max_staff_weekday
                }
        
        # Check staffing feasibility per shift
        diagnostics['shift_analysis'] = {}
        for shift_code in shift_codes:
            if shift_code not in staffing_weekday:
                continue
            
            min_required = staffing_weekday[shift_code]["min"]
            
            # Count employees in teams that can work this shift
            eligible_employees = 0
            for team in teams:
                # Check if team can work this shift
                if team.allowed_shift_type_ids:
                    # Team has restrictions
                    shift_type = None
                    if shift_types:
                        for st in shift_types:
                            if st.code == shift_code:
                                shift_type = st
                                break
                    
                    if shift_type and shift_type.id in team.allowed_shift_type_ids:
                        # Team can work this shift
                        eligible_employees += len([e for e in employees if e.team_id == team.id])
                else:
                    # Team can work all shifts (backward compatible)
                    eligible_employees += len([e for e in employees if e.team_id == team.id])
            
            diagnostics['shift_analysis'][shift_code] = {
                'min_required': min_required,
                'eligible_employees': eligible_employees,
                'is_feasible': eligible_employees >= min_required
            }
            
            if eligible_employees < min_required:
                diagnostics['potential_issues'].append(
                    f"Schicht {shift_code}: Benötigt {min_required} Mitarbeiter, nur {eligible_employees} verfügbar"
                )
        
        # Check team sizes and rotation feasibility
        diagnostics['team_analysis'] = {}
        rotation_shifts = ['F', 'N', 'S']
        teams_in_rotation = 0
        
        for team in teams:
            team_size = len([e for e in employees if e.team_id == team.id])
            
            # Check if team participates in F-N-S rotation
            can_rotate = True
            if team.allowed_shift_type_ids and shift_types:
                # Check if team has all rotation shifts
                rotation_shift_ids = []
                for st in shift_types:
                    if st.code in rotation_shifts:
                        rotation_shift_ids.append(st.id)
                
                can_rotate = all(sid in team.allowed_shift_type_ids for sid in rotation_shift_ids)
            
            if can_rotate:
                teams_in_rotation += 1
            
            diagnostics['team_analysis'][team.name] = {
                'size': team_size,
                'allowed_shifts': team.allowed_shift_type_ids if team.allowed_shift_type_ids else "all",
                'participates_in_rotation': can_rotate
            }
            
            if team_size < 3:
                diagnostics['potential_issues'].append(
                    f"Team {team.name} hat nur {team_size} Mitglieder (möglicherweise zu klein für Rotation)"
                )
        
        # Check if rotation pattern can be satisfied
        # Need at least 3 teams for F-N-S rotation to meet all shift requirements simultaneously
        if teams_in_rotation < 3:
            diagnostics['potential_issues'].append(
                f"Nur {teams_in_rotation} Teams können F-N-S-Rotation durchführen (3 empfohlen für gleichzeitige Abdeckung)"
            )
        
        # Check for excessive absences
        if absence_ratio > 0.3:
            diagnostics['potential_issues'].append(
                f"Hohe Abwesenheitsrate: {absence_ratio*100:.1f}% aller Mitarbeitertage sind durch Abwesenheiten belegt"
            )
        
        # Check planning period constraints
        actual_weeks = len(dates) / 7.0
        if actual_weeks < 3:
            diagnostics['potential_issues'].append(
                f"Planungszeitraum ist nur {actual_weeks:.1f} Woche(n). Rotationsmuster (F→N→S) funktioniert am besten mit 3+ Wochen."
            )
        
        # Additional feasibility checks based on working hours and constraints
        # Check if total available working capacity meets minimum requirements
        # Note: This is a simplified capacity check based on shift minimums and max consecutive days.
        # It doesn't account for complex constraint interactions (rest times, weekend patterns, etc.)
        # but provides a useful upper-bound feasibility check.
        
        # Constants for capacity calculation
        # Note: MIN_CAPACITY_RATIO is a heuristic warning threshold, not a hard constraint.
        # The solver will still attempt planning even if capacity is below this threshold.
        MIN_CAPACITY_RATIO = 1.1  # Recommended 10% buffer for better feasibility (was 1.2)
        MAX_TEAM_SIZE_IMBALANCE_RATIO = 2.0  # Max ratio between largest and smallest team
        
        total_shifts_needed = len(dates) * len(shift_codes)  # Total shift slots
        total_employee_capacity = len(employees) * len(dates)
        available_capacity = total_employee_capacity - absent_days
        
        # Each employee can work max 6 consecutive days, so effective capacity is reduced
        max_consecutive = 6
        # Note: Using calendar weeks here (not actual weeks) to count rest periods needed.
        # Each calendar week requires one rest day, regardless of whether it's a full week.
        weeks_in_period = len(weeks)
        effective_capacity_per_employee = min(
            len(dates),  # Can't work more days than exist
            (weeks_in_period * max_consecutive)  # Max consecutive constraint (approx)
        )
        total_effective_capacity = len(employees) * effective_capacity_per_employee - absent_days
        
        # Check if we have enough theoretical capacity
        # Need at least min_staff per shift per day
        min_capacity_needed = 0
        for shift_code in shift_codes:
            if shift_code in staffing_weekday:
                min_staff = staffing_weekday[shift_code]["min"]
                # Simplified: assume each shift needs min_staff for all days
                # This doesn't distinguish weekday/weekend but provides a conservative estimate
                min_capacity_needed += min_staff * len(dates)
        
        capacity_ratio = total_effective_capacity / min_capacity_needed if min_capacity_needed > 0 else 0
        
        if capacity_ratio < MIN_CAPACITY_RATIO:
            diagnostics['potential_issues'].append(
                f"Knappe Personalkapazität: {capacity_ratio:.2f}x der Mindestanforderung (empfohlen: ≥{MIN_CAPACITY_RATIO}x für optimale Planbarkeit). "
                f"Effektive Kapazität: {total_effective_capacity} Mitarbeitertage, "
                f"Mindestbedarf: {min_capacity_needed} Mitarbeitertage. "
                f"Planung kann trotzdem funktionieren, erfordert aber möglicherweise mehr Lösungszeit."
            )
        
        # Check for specific constraint violations
        # If many employees are on the same team, rotation might be too rigid
        team_sizes = [len([e for e in employees if e.team_id == t.id]) for t in teams]
        if team_sizes:
            max_team_size = max(team_sizes)
            min_team_size = min(team_sizes)
            if max_team_size > min_team_size * MAX_TEAM_SIZE_IMBALANCE_RATIO:
                diagnostics['potential_issues'].append(
                    f"Ungleiche Teamgrößen: Größtes Team hat {max_team_size} Mitglieder, "
                    f"kleinstes nur {min_team_size}. Dies kann zu Planungsproblemen führen."
                )
        
        # NEW: Check for partial week conflicts
        # Partial weeks (< 7 days) can create impossible situations with team rotation
        week_sizes = [len(week) for week in weeks]
        partial_weeks = [i for i, size in enumerate(week_sizes) if size < 7]
        
        if partial_weeks:
            # Check if partial weeks could conflict with staffing requirements
            for week_idx in partial_weeks:
                week = weeks[week_idx]
                week_size = len(week)
                weekdays_in_week = sum(1 for d in week if d.weekday() < 5)
                weekends_in_week = week_size - weekdays_in_week
                
                # Calculate minimum staff needed for this partial week
                # Check how many teams participate in F→N→S rotation
                rotation_shift_codes = ['F', 'N', 'S']
                participating_teams = sum(1 for t in teams if all(
                    code in shift_codes for code in rotation_shift_codes
                ))
                
                if participating_teams >= len(rotation_shift_codes):
                    # Each team will be assigned one shift for this week
                    # Check if smallest team can meet staffing requirements
                    if team_sizes:
                        smallest_team = min(team_sizes)
                        
                        # Check against shift requirements
                        for shift_code in shift_codes:
                            if shift_code not in staffing_weekday:
                                continue
                            
                            min_weekday = staffing_weekday[shift_code]["min"]
                            
                            # For a partial week, a team might need to provide min_weekday staff
                            # on all weekdays in that week
                            if weekdays_in_week > 0 and smallest_team < min_weekday:
                                # CRITICAL: Team too small to meet minimum staffing
                                diagnostics['potential_issues'].append(
                                    f"Woche {week_idx + 1} ({week[0].strftime('%d.%m')} - {week[-1].strftime('%d.%m')}) "
                                    f"ist eine Teilwoche mit nur {week_size} Tagen ({weekdays_in_week} Werktage). "
                                    f"Kleinstes Team ({smallest_team} Mitarbeiter) kann Mindestbesetzung von "
                                    f"{min_weekday} für Schicht {shift_code} nicht erfüllen. "
                                    f"Dies macht die Rotation unmöglich."
                                )
                                break  # Only report once per partial week
        
        # NEW: Check if planning period starts on a day other than Monday
        # This creates a partial first week which can cause rotation conflicts
        # NOTE: In the Web UI, this is automatically handled by extending to complete weeks
        first_date = dates[0]
        last_date = dates[-1]
        if first_date.weekday() != 0:  # Not Monday
            # Calculate days in first week (from first_date until Sunday)
            days_in_first_week = 7 - first_date.weekday()
            diagnostics['potential_issues'].append(
                f"Planungszeitraum beginnt am {first_date.strftime('%A, %d.%m.%Y')} "
                f"(nicht Montag). Dies erzeugt eine unvollständige erste Woche mit nur "
                f"{days_in_first_week} Tagen, was zu Konflikten mit der Team-Rotation und "
                f"Mindestbesetzungsanforderungen führen kann. "
                f"HINWEIS: Das System erweitert automatisch auf vollständige Wochen (Mo-So) "
                f"und berücksichtigt bereits geplante Tage aus dem Vormonat."
            )
        
        # NEW: Check if last week is also partial
        if last_date.weekday() != 6 and len(weeks) > 0:  # Not Sunday
            last_week_size = len(weeks[-1])
            if last_week_size < 7:
                diagnostics['potential_issues'].append(
                    f"Planungszeitraum endet am {last_date.strftime('%A, %d.%m.%Y')} "
                    f"(nicht Sonntag). Dies erzeugt eine unvollständige letzte Woche mit nur "
                    f"{last_week_size} Tagen, was zu Planungsproblemen führen kann. "
                    f"HINWEIS: Das System erweitert automatisch auf vollständige Wochen (Mo-So) "
                    f"und plant monatsübergreifend bis zum nächsten Sonntag."
                )
        
        # NEW: Check rotation pattern feasibility with actual planning weeks
        # If we have exactly 5 weeks and teams rotate F→N→S, check if this creates conflicts
        if len(weeks) == 5 and len(teams) == 3:
            # With 3 teams and F→N→S rotation, week pattern repeats every 3 weeks
            # Having 5 weeks means some teams will have same shift type 2 times (weeks 0,3 and 1,4 or 2,5)
            # This is fine normally, but with partial weeks it can create problems
            if len(partial_weeks) >= 2:
                diagnostics['potential_issues'].append(
                    f"Planungszeitraum hat {len(weeks)} Wochen mit {len(partial_weeks)} Teilwochen. "
                    f"Bei 3-Team-Rotation (F→N→S) kann dies zu Konflikten führen, da manche Teams "
                    f"dieselbe Schicht mehrmals übernehmen müssen und Teilwochen die Besetzung erschweren."
                )
        
        return diagnostics
    
    def solve(self) -> bool:
        """
        Solve the shift planning problem.
        
        Returns:
            True if a solution was found, False otherwise
        """
        model = self.planning_model.get_model()
        
        # Configure solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = self.num_workers
        solver.parameters.log_search_progress = True
        
        print("\n" + "=" * 60)
        print("STARTING SOLVER")
        print("=" * 60)
        print(f"Time limit: {self.time_limit_seconds} seconds")
        print(f"Parallel workers: {self.num_workers}")
        print()
        
        # Solve
        self.status = solver.Solve(model)
        self.solution = solver
        
        # Print results
        print("\n" + "=" * 60)
        print("SOLVER RESULTS")
        print("=" * 60)
        
        if self.status == cp_model.OPTIMAL:
            print("✓ OPTIMAL solution found!")
        elif self.status == cp_model.FEASIBLE:
            print("✓ FEASIBLE solution found (not proven optimal)")
        elif self.status == cp_model.INFEASIBLE:
            print("✗ INFEASIBLE - No solution exists!")
            print("\nRunning diagnostics to identify the issue...")
            diagnostics = self.diagnose_infeasibility()
            
            print(f"\nModel Statistics:")
            print(f"  - Total employees: {diagnostics['total_employees']}")
            print(f"  - Available employees: {diagnostics['available_employees']}")
            print(f"  - Absent employees: {diagnostics['absent_employees']}")
            print(f"  - Planning period: {diagnostics['planning_days']} days")
            
            if diagnostics['potential_issues']:
                print(f"\n⚠️  Potential Issues Detected ({len(diagnostics['potential_issues'])}):")
                for issue in diagnostics['potential_issues']:
                    print(f"  • {issue}")
            
            print(f"\nShift Staffing Analysis:")
            for shift_code, analysis in diagnostics['shift_analysis'].items():
                status = "✓" if analysis['is_feasible'] else "✗"
                print(f"  {status} {shift_code}: {analysis['eligible_employees']} eligible / {analysis['min_required']} required")
            
            print(f"\nTeam Configuration:")
            for team_name, info in diagnostics['team_analysis'].items():
                allowed = info['allowed_shifts'] if isinstance(info['allowed_shifts'], str) else f"{len(info['allowed_shifts'])} specific shifts"
                print(f"  - {team_name}: {info['size']} members, allowed shifts: {allowed}")
            
            # Store diagnostics for later use
            self.diagnostics = diagnostics
            return False
        elif self.status == cp_model.MODEL_INVALID:
            print("✗ MODEL INVALID - Check constraints!")
            return False
        else:
            print(f"✗ Unknown status: {self.status}")
            return False
        
        print(f"\nSolver statistics:")
        print(f"  - Wall time: {solver.WallTime():.2f} seconds")
        print(f"  - Branches: {solver.NumBranches()}")
        print(f"  - Conflicts: {solver.NumConflicts()}")
        if self.status == cp_model.OPTIMAL or self.status == cp_model.FEASIBLE:
            print(f"  - Objective value: {solver.ObjectiveValue()}")
        
        print("=" * 60)
        
        return True
    
    def extract_solution(self) -> Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str], Dict[Tuple[int, date], str]]:
        """
        Extract shift assignments from the TEAM-BASED solution with CROSS-TEAM support.
        
        Returns:
            Tuple of (shift_assignments, special_functions, complete_schedule)
            where:
            - shift_assignments: List of ShiftAssignment objects (includes cross-team assignments)
            - special_functions: dict mapping (employee_id, date) to "TD"
            - complete_schedule: dict mapping (employee_id, date) to shift_code or "OFF"
                                This ensures ALL employees appear for ALL days
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return [], {}, {}
        
        (team_shift, employee_active, employee_weekend_shift, 
         employee_cross_team_shift, employee_cross_team_weekend, td_vars) = self.planning_model.get_variables()
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_codes = self.planning_model.shift_codes
        absences = self.planning_model.absences
        
        assignments = []
        assignment_id = 1
        
        # Complete schedule: every employee, every day
        complete_schedule = {}
        
        # Track assigned shifts to prevent double assignments (safety check)
        # Maps (employee_id, date) -> shift_type_id
        assigned_shifts = {}
        
        # Helper function to safely add assignment (prevents double shifts)
        def try_add_assignment(emp_id, shift_type_id, d, notes=None):
            """
            Try to add an assignment, preventing double shifts.
            Returns True if added, False if prevented.
            """
            nonlocal assignment_id, assignments, assigned_shifts
            
            # Safety check: prevent double assignment
            if (emp_id, d) in assigned_shifts:
                print(f"WARNING: Double shift assignment prevented for employee {emp_id} on {d}")
                print(f"  Already assigned: {assigned_shifts[(emp_id, d)]}, attempted: {shift_type_id}")
                return False
            
            # Create and add assignment
            assignment = ShiftAssignment(
                id=assignment_id,
                employee_id=emp_id,
                shift_type_id=shift_type_id,
                date=d,
                notes=notes
            )
            assignments.append(assignment)
            assigned_shifts[(emp_id, d)] = shift_type_id
            assignment_id += 1
            return True
        
        # Extract shift assignments based on team shifts and employee activity
        for emp in employees:
            # Regular team members
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
            
            # For each date, check if employee is active
            for d in dates:
                weekday = d.weekday()
                
                if weekday < 5:  # WEEKDAY (Mon-Fri): Use team shift
                    if (emp.id, d) not in employee_active:
                        continue
                    
                    if self.solution.Value(employee_active[(emp.id, d)]) == 0:
                        continue  # Not working this day
                    
                    # Find which week this date belongs to
                    week_idx = self.planning_model.get_week_index(d)
                    
                    # Find which shift the team has this week
                    team_shift_code = None
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            if self.solution.Value(team_shift[(team.id, week_idx, shift_code)]) == 1:
                                team_shift_code = shift_code
                                break
                    
                    if not team_shift_code:
                        continue  # No shift found
                    
                    # Find shift type ID
                    shift_type_id = None
                    for st in STANDARD_SHIFT_TYPES:
                        if st.code == team_shift_code:
                            shift_type_id = st.id
                            break
                    
                    if shift_type_id:
                        try_add_assignment(emp.id, shift_type_id, d)
                
                else:  # WEEKEND (Sat-Sun): Use team shift type with individual presence
                    # Check if employee is working this weekend day
                    if (emp.id, d) not in employee_weekend_shift:
                        continue
                    
                    if self.solution.Value(employee_weekend_shift[(emp.id, d)]) == 0:
                        continue  # Not working this weekend day
                    
                    # Find which week this date belongs to
                    week_idx = self.planning_model.get_week_index(d)
                    
                    # Find which shift the team has this week (same for weekends)
                    team_shift_code = None
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            if self.solution.Value(team_shift[(team.id, week_idx, shift_code)]) == 1:
                                team_shift_code = shift_code
                                break
                    
                    if not team_shift_code:
                        continue  # No shift found
                    
                    # Find shift type ID
                    shift_type_id = None
                    for st in STANDARD_SHIFT_TYPES:
                        if st.code == team_shift_code:
                            shift_type_id = st.id
                            break
                    
                    if shift_type_id:
                        try_add_assignment(emp.id, shift_type_id, d)
        
        # Extract CROSS-TEAM assignments (NEW)
        # These are employees working shifts from other teams to meet their monthly hours
        for emp in employees:
            if not emp.team_id:
                continue
            
            for d in dates:
                weekday = d.weekday()
                
                if weekday < 5:  # WEEKDAY cross-team
                    # Check all shift codes this employee can work cross-team
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) not in employee_cross_team_shift:
                            continue
                        
                        if self.solution.Value(employee_cross_team_shift[(emp.id, d, shift_code)]) == 1:
                            # Find shift type ID
                            shift_type_id = None
                            for st in STANDARD_SHIFT_TYPES:
                                if st.code == shift_code:
                                    shift_type_id = st.id
                                    break
                            
                            if shift_type_id:
                                if try_add_assignment(emp.id, shift_type_id, d, "Cross-team assignment"):
                                    break  # Only one shift per day
                
                else:  # WEEKEND cross-team
                    # Check all shift codes this employee can work cross-team on weekends
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) not in employee_cross_team_weekend:
                            continue
                        
                        if self.solution.Value(employee_cross_team_weekend[(emp.id, d, shift_code)]) == 1:
                            # Find shift type ID
                            shift_type_id = None
                            for st in STANDARD_SHIFT_TYPES:
                                if st.code == shift_code:
                                    shift_type_id = st.id
                                    break
                            
                            if shift_type_id:
                                if try_add_assignment(emp.id, shift_type_id, d, "Cross-team weekend assignment"):
                                    break  # Only one shift per day
        
        # Extract TD assignments
        special_functions = {}
        
        for emp in employees:
            if not emp.can_do_td:
                continue
            
            for week_idx, week_dates in enumerate(weeks):
                if (emp.id, week_idx) not in td_vars:
                    continue
                
                if self.solution.Value(td_vars[(emp.id, week_idx)]) == 1:
                    # Mark TD for all weekdays in this week
                    for d in week_dates:
                        if d.weekday() < 5:  # Monday to Friday
                            special_functions[(emp.id, d)] = "TD"
        
        # Build complete schedule: every employee for every day
        # This ensures ALL employees appear in the output, even without shifts
        # 
        # CRITICAL: Absences (U, AU, L) ALWAYS take priority over shifts and TD
        # This is mandated by requirement #1 in the problem statement:
        # "Absence codes (U, AU, L) ALWAYS override regular shifts and TD"
        # 
        # Priority order (highest to lowest):
        # 1. Absence (U, AU, L)
        # 2. TD (Day Duty)
        # 3. Regular shifts (F, S, N)
        # 4. OFF (no assignment)
        for emp in employees:
            for d in dates:
                # PRIORITY 1: Check if employee is absent (HIGHEST PRIORITY)
                # Absences ALWAYS override shifts and TD
                absence = None
                for abs in absences:
                    if abs.employee_id == emp.id and abs.overlaps_date(d):
                        absence = abs
                        break
                
                if absence:
                    # Show absence code (U, AU, or L)
                    complete_schedule[(emp.id, d)] = absence.get_code()
                    continue
                
                # PRIORITY 2: Check if employee has TD on this day
                if (emp.id, d) in special_functions:
                    complete_schedule[(emp.id, d)] = "TD"
                    continue
                
                # PRIORITY 3: Check if employee has a shift assignment
                has_assignment = False
                for assignment in assignments:
                    if assignment.employee_id == emp.id and assignment.date == d:
                        # Get shift code
                        shift_type = next((st for st in STANDARD_SHIFT_TYPES if st.id == assignment.shift_type_id), None)
                        if shift_type:
                            complete_schedule[(emp.id, d)] = shift_type.code
                            has_assignment = True
                            break
                
                # PRIORITY 4: No assignment - mark as OFF
                if not has_assignment:
                    complete_schedule[(emp.id, d)] = "OFF"
        
        return assignments, special_functions, complete_schedule
    
    def print_planning_summary(
        self,
        assignments: List[ShiftAssignment],
        special_functions: Dict[Tuple[int, date], str],
        complete_schedule: Dict[Tuple[int, date], str]
    ):
        """
        Print a comprehensive summary of the planning results.
        
        Shows:
        - Planning period details (days, weeks)
        - Shift distribution per shift type
        - Required monthly working hours per employee
        - Actual hours worked per employee
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return
        
        from collections import defaultdict
        from datetime import timedelta
        
        employees = self.planning_model.employees
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_types = self.planning_model.shift_types
        absences = self.planning_model.absences
        
        print("\n" + "=" * 80)
        print("SCHICHTPLAN ZUSAMMENFASSUNG (PLANNING SUMMARY)")
        print("=" * 80)
        
        # Planning period details
        start_date = dates[0]
        end_date = dates[-1]
        total_days = len(dates)
        total_weeks = len(weeks)
        
        # Determine month name from start date
        month_names = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                      "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month_name = month_names[start_date.month - 1]
        
        print(f"\nPlanungszeitraum:")
        print(f"  Von: {start_date.strftime('%d.%m.%Y')} ({start_date.strftime('%A')})")
        print(f"  Bis: {end_date.strftime('%d.%m.%Y')} ({end_date.strftime('%A')})")
        print(f"  Tage im Planungszeitraum: {total_days}")
        print(f"  Wochen im Planungszeitraum: {total_weeks}")
        print(f"  Monat: {month_name} {start_date.year}")
        
        # Count shifts per shift type
        shift_counts = defaultdict(int)
        for assignment in assignments:
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            if shift_type:
                shift_counts[shift_type.code] += 1
        
        print(f"\nAnzahl Schichten je Schichtart:")
        for shift_code in sorted(shift_counts.keys()):
            count = shift_counts[shift_code]
            shift_type = next((st for st in shift_types if st.code == shift_code), None)
            shift_name = shift_type.name if shift_type else shift_code
            print(f"  {shift_code} ({shift_name}): {count} Schichten")
        
        # Count TD assignments
        td_count = len(set(emp_id for (emp_id, d), func in special_functions.items() if func == "TD"))
        if td_count > 0:
            print(f"  TD (Tagdienst): {td_count} Zuweisungen über {total_weeks} Wochen")
        
        # Calculate required and actual hours per employee
        print(f"\nMonatliche Arbeitsstunden je Mitarbeiter:")
        print(f"  {'Mitarbeiter':<30} {'Soll (h)':<12} {'Ist (h)':<12} {'Differenz':<12} {'Tage':<8}")
        print(f"  {'-' * 74}")
        
        emp_hours = {}
        emp_days = {}
        
        for assignment in assignments:
            emp_id = assignment.employee_id
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            
            if emp_id not in emp_hours:
                emp_hours[emp_id] = 0
                emp_days[emp_id] = set()
            
            emp_hours[emp_id] += shift_type.hours
            emp_days[emp_id].add(assignment.date)
        
        # Calculate required hours for each employee
        for emp in sorted(employees, key=lambda e: e.full_name):
            if not emp.team_id:
                continue  # Skip employees without teams
            
            # Find employee's shift type to get weekly working hours
            weekly_hours = 40.0  # Default
            if shift_types:
                # Use first shift type as default
                for st in shift_types:
                    if st.code in ['F', 'S', 'N']:
                        weekly_hours = st.weekly_working_hours
                        break
            
            # Count days without absence for this employee
            days_without_absence = 0
            for d in dates:
                is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) 
                              for abs in absences)
                if not is_absent:
                    days_without_absence += 1
            
            # Calculate required hours: (weekly_hours / 7) × days_without_absence
            required_hours = (weekly_hours / 7.0) * days_without_absence
            
            # Get actual hours
            actual_hours = emp_hours.get(emp.id, 0)
            actual_days = len(emp_days.get(emp.id, set()))
            
            # Calculate difference
            diff = actual_hours - required_hours
            diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
            
            # Only show employees with hours
            if actual_hours > 0 or days_without_absence > 0:
                print(f"  {emp.full_name:<30} {required_hours:>10.1f}h  {actual_hours:>10.1f}h  {diff_str:>10}h  {actual_days:>6}")
        
        # Summary statistics
        total_assignments = len(assignments)
        total_employees_working = len(emp_hours)
        
        print(f"\nGesamtstatistik:")
        print(f"  Gesamtanzahl Schichtzuweisungen: {total_assignments}")
        print(f"  Anzahl arbeitender Mitarbeiter: {total_employees_working}/{len([e for e in employees if e.team_id])}")
        
        avg_hours = sum(emp_hours.values()) / len(emp_hours) if emp_hours else 0
        print(f"  Durchschnittliche Stunden pro Mitarbeiter: {avg_hours:.1f}h")
        
        print("=" * 80)
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get solution statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.solution:
            return {}
        
        return {
            "status": "OPTIMAL" if self.status == cp_model.OPTIMAL else "FEASIBLE",
            "wall_time": self.solution.WallTime(),
            "branches": self.solution.NumBranches(),
            "conflicts": self.solution.NumConflicts(),
            "objective_value": self.solution.ObjectiveValue() if self.status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None
        }


def solve_shift_planning(
    planning_model: ShiftPlanningModel,
    time_limit_seconds: int = 300,
    num_workers: int = 8,
    global_settings: Dict = None
) -> Optional[Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str], Dict[Tuple[int, date], str]]]:
    """
    Solve the shift planning problem.
    
    Args:
        planning_model: The shift planning model
        time_limit_seconds: Maximum time for solver
        num_workers: Number of parallel workers
        global_settings: Dict with global settings from database (optional)
        
    Returns:
        Tuple of (shift_assignments, special_functions, complete_schedule) if solution found, None otherwise
        where:
        - shift_assignments: List of ShiftAssignment objects for employees who work
        - special_functions: dict mapping (employee_id, date) to "TD" for day duty assignments
        - complete_schedule: dict mapping (employee_id, date) to shift_code/"OFF"/"ABSENT"/"TD"
                            ensuring ALL employees appear for ALL days
    
    Note: When None is returned (no solution found), diagnostic information is printed to stdout.
          To get structured diagnostic data, check solver.diagnostics attribute after calling solver.solve()
    """
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds, num_workers, global_settings)
    solver.add_all_constraints()
    
    if solver.solve():
        result = solver.extract_solution()
        assignments, special_functions, complete_schedule = result
        
        # Print comprehensive planning summary
        solver.print_planning_summary(assignments, special_functions, complete_schedule)
        
        return result
    else:
        # Diagnostics are already printed in solver.solve() when INFEASIBLE
        return None


def get_infeasibility_diagnostics(
    planning_model: ShiftPlanningModel
) -> Dict[str, any]:
    """
    Get diagnostic information about potential infeasibility without running the solver.
    
    This is useful for pre-checking if a planning configuration is likely to succeed.
    
    Args:
        planning_model: The shift planning model to analyze
        
    Returns:
        Dictionary with diagnostic information
    """
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds=1, num_workers=1)
    return solver.diagnose_infeasibility()


if __name__ == "__main__":
    # Test solver
    from data_loader import generate_sample_data
    from model import create_shift_planning_model
    from datetime import timedelta
    
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=13)  # 2 weeks
    
    print("Creating model...")
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    planning_model.print_model_statistics()
    
    print("\nSolving...")
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
        print(f"  - Complete schedule entries: {len(complete_schedule)}")
    else:
        print("\n✗ No solution found!")
