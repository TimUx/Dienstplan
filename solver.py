"""
Solver for the TEAM-BASED shift planning problem using OR-Tools CP-SAT.
Configures and runs the solver, returns solution.
"""

from ortools.sat.python import cp_model
from datetime import date
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
    WEEKDAY_STAFFING
)


class ShiftPlanningSolver:
    """
    Solver for the shift planning problem.
    """
    
    def __init__(
        self,
        planning_model: ShiftPlanningModel,
        time_limit_seconds: int = 300,
        num_workers: int = 8
    ):
        """
        Initialize the solver.
        
        Args:
            planning_model: The shift planning model
            time_limit_seconds: Maximum time for solver (default 5 minutes)
            num_workers: Number of parallel workers for solver
        """
        self.planning_model = planning_model
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self.solution = None
        self.status = None
    
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
        add_employee_team_linkage_constraints(model, team_shift, employee_active, employee_cross_team_shift, employees, teams, dates, weeks, shift_codes, absences)
        
        # STAFFING AND WORKING CONDITIONS
        print("  - Staffing requirements (min/max per shift, including cross-team)")
        add_staffing_constraints(model, employee_active, employee_weekend_shift, team_shift, 
                                employee_cross_team_shift, employee_cross_team_weekend, 
                                employees, teams, dates, weeks, shift_codes, shift_types)
        
        print("  - Rest time constraints (11 hours minimum, enforced for cross-team)")
        add_rest_time_constraints(model, employee_active, employee_weekend_shift, team_shift, 
                                 employee_cross_team_shift, employee_cross_team_weekend, 
                                 employees, dates, weeks, shift_codes, teams)
        
        print("  - Consecutive shifts constraints (max 6 days, including cross-team)")
        add_consecutive_shifts_constraints(model, employee_active, employee_weekend_shift, 
                                          employee_cross_team_shift, employee_cross_team_weekend, 
                                          td_vars, employees, dates, shift_codes)
        
        print("  - Working hours constraints (dynamic based on shift configuration, including cross-team)")
        add_working_hours_constraints(model, employee_active, employee_weekend_shift, team_shift, 
                                     employee_cross_team_shift, employee_cross_team_weekend, 
                                     td_vars, employees, teams, dates, weeks, shift_codes, shift_types, absences)
        
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
        print("  - Fairness objectives (per-employee, including block scheduling)")
        objective_terms = add_fairness_objectives(model, employee_active, employee_weekend_shift, team_shift, 
                                                  employee_cross_team_shift, employee_cross_team_weekend, 
                                                  td_vars, employees, teams, dates, weeks, shift_codes)
        
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
        
        # Build staffing requirements from shift_types
        if shift_types:
            staffing_weekday = {}
            for st in shift_types:
                if st.code in shift_codes:
                    staffing_weekday[st.code] = {
                        "min": st.min_staff_weekday,
                        "max": st.max_staff_weekday
                    }
        else:
            # Use default values imported at module level
            staffing_weekday = WEEKDAY_STAFFING
        
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
        MIN_CAPACITY_RATIO = 1.2  # Need 20% buffer for feasibility
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
                f"Zu wenig Personalkapazität: {capacity_ratio:.1f}x der Mindestanforderung (empfohlen: ≥{MIN_CAPACITY_RATIO}x). "
                f"Effektive Kapazität: {total_effective_capacity} Mitarbeitertage, "
                f"Mindestbedarf: {min_capacity_needed} Mitarbeitertage"
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
                        assignment = ShiftAssignment(
                            id=assignment_id,
                            employee_id=emp.id,
                            shift_type_id=shift_type_id,
                            date=d
                        )
                        assignments.append(assignment)
                        assignment_id += 1
                
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
                        assignment = ShiftAssignment(
                            id=assignment_id,
                            employee_id=emp.id,
                            shift_type_id=shift_type_id,
                            date=d
                        )
                        assignments.append(assignment)
                        assignment_id += 1
        
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
                                assignment = ShiftAssignment(
                                    id=assignment_id,
                                    employee_id=emp.id,
                                    shift_type_id=shift_type_id,
                                    date=d,
                                    notes="Cross-team assignment"
                                )
                                assignments.append(assignment)
                                assignment_id += 1
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
                                assignment = ShiftAssignment(
                                    id=assignment_id,
                                    employee_id=emp.id,
                                    shift_type_id=shift_type_id,
                                    date=d,
                                    notes="Cross-team weekend assignment"
                                )
                                assignments.append(assignment)
                                assignment_id += 1
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
    num_workers: int = 8
) -> Optional[Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str], Dict[Tuple[int, date], str]]]:
    """
    Solve the shift planning problem.
    
    Args:
        planning_model: The shift planning model
        time_limit_seconds: Maximum time for solver
        num_workers: Number of parallel workers
        
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
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds, num_workers)
    solver.add_all_constraints()
    
    if solver.solve():
        return solver.extract_solution()
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
