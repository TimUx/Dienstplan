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
    add_fairness_objectives
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
        Add all constraints to the TEAM-BASED model.
        """
        model = self.planning_model.get_model()
        team_shift, employee_active, employee_weekend_shift, td_vars, ferienjobber_cross_team = self.planning_model.get_variables()
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
        add_team_shift_assignment_constraints(model, team_shift, teams, weeks, shift_codes)
        
        print("  - Team rotation (F → N → S pattern)")
        add_team_rotation_constraints(model, team_shift, teams, weeks, shift_codes, locked_team_shift)
        
        print("  - Employee-team linkage (derive employee activity from team shifts)")
        add_employee_team_linkage_constraints(model, team_shift, employee_active, ferienjobber_cross_team, employees, teams, dates, weeks, shift_codes, absences)
        
        # STAFFING AND WORKING CONDITIONS
        print("  - Staffing requirements (min/max per shift)")
        add_staffing_constraints(model, employee_active, employee_weekend_shift, team_shift, ferienjobber_cross_team, employees, teams, dates, weeks, shift_codes)
        
        print("  - Rest time constraints (11 hours minimum)")
        add_rest_time_constraints(model, employee_active, employee_weekend_shift, team_shift, employees, dates, weeks, shift_codes)
        
        print("  - Consecutive shifts constraints (max 6 days)")
        add_consecutive_shifts_constraints(model, employee_active, employee_weekend_shift, td_vars, employees, dates, shift_codes)
        
        print("  - Working hours constraints (dynamic based on shift configuration)")
        add_working_hours_constraints(model, employee_active, employee_weekend_shift, team_shift, td_vars, employees, teams, dates, weeks, shift_codes, shift_types)
        
        # SPECIAL FUNCTIONS
        print("  - TD constraints (Tagdienst = organizational marker)")
        add_td_constraints(model, employee_active, td_vars, employees, dates, weeks, absences)
        
        print("  - Weekly available employee constraint (at least 1 free per week)")
        add_weekly_available_employee_constraint(model, employee_active, employee_weekend_shift, employees, teams, weeks)
        
        # SOFT CONSTRAINTS (OPTIMIZATION)
        print("  - Fairness objectives")
        objective_terms = add_fairness_objectives(model, employee_active, employee_weekend_shift, team_shift, td_vars, ferienjobber_cross_team, employees, teams, dates, weeks, shift_codes)
        
        # Set objective function (minimize sum of objective terms)
        if objective_terms:
            model.Minimize(sum(objective_terms))
        
        print("All constraints added successfully!")
    
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
        Extract shift assignments from the TEAM-BASED solution.
        
        Returns:
            Tuple of (shift_assignments, special_functions, complete_schedule)
            where:
            - shift_assignments: List of ShiftAssignment objects
            - special_functions: dict mapping (employee_id, date) to "TD"
            - complete_schedule: dict mapping (employee_id, date) to shift_code or "OFF"
                                This ensures ALL employees appear for ALL days
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return [], {}, {}
        
        team_shift, employee_active, employee_weekend_shift, td_vars, ferienjobber_cross_team = self.planning_model.get_variables()
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
    """
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds, num_workers)
    solver.add_all_constraints()
    
    if solver.solve():
        return solver.extract_solution()
    else:
        return None


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
