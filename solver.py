"""
Solver for the shift planning problem using OR-Tools CP-SAT.
Configures and runs the solver, returns solution.
"""

from ortools.sat.python import cp_model
from datetime import date
from typing import List, Dict, Tuple, Optional
from entities import Employee, ShiftAssignment, STANDARD_SHIFT_TYPES
from model import ShiftPlanningModel
from constraints import (
    add_basic_constraints,
    add_staffing_constraints,
    add_rest_time_constraints,
    add_consecutive_shifts_constraints,
    add_working_hours_constraints,
    add_special_function_constraints,
    add_springer_constraints,
    add_team_rotation_constraints,
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
        Add all constraints to the model.
        """
        model = self.planning_model.get_model()
        x, bmt_vars, bsb_vars = self.planning_model.get_variables()
        employees = self.planning_model.employees
        dates = self.planning_model.dates
        shift_codes = self.planning_model.shift_codes
        absences = self.planning_model.absences
        shift_types = self.planning_model.shift_types
        
        print("Adding constraints...")
        
        # Hard constraints (must be satisfied)
        print("  - Basic constraints (one shift per day, no work when absent)")
        add_basic_constraints(model, x, employees, dates, shift_codes, absences)
        
        print("  - Staffing requirements (min/max per shift)")
        add_staffing_constraints(model, x, employees, dates, shift_codes)
        
        print("  - Rest time constraints (11 hours minimum)")
        add_rest_time_constraints(model, x, employees, dates, shift_codes)
        
        print("  - Consecutive shifts constraints (max 6 days, max 5 nights)")
        add_consecutive_shifts_constraints(model, x, bmt_vars, bsb_vars, employees, dates, shift_codes)
        
        print("  - Working hours constraints (48h/week, 192h/month)")
        add_working_hours_constraints(model, x, bmt_vars, bsb_vars, employees, dates, shift_codes, shift_types)
        
        print("  - Special function constraints (BMT, BSB)")
        add_special_function_constraints(model, x, bmt_vars, bsb_vars, employees, dates, absences)
        
        print("  - Springer constraints (at least 1 available)")
        add_springer_constraints(model, x, employees, dates, shift_codes)
        
        print("  - Team rotation constraints (weekly rotation)")
        add_team_rotation_constraints(model, x, employees, dates, shift_codes)
        
        # Soft constraints (optimization objectives)
        print("  - Fairness objectives")
        objective_terms = add_fairness_objectives(model, x, employees, dates, shift_codes)
        
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
    
    def extract_solution(self) -> Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str]]:
        """
        Extract shift assignments from the solution.
        
        Returns:
            Tuple of (shift_assignments, special_functions)
            where special_functions is a dict mapping (employee_id, date) to function type ("BMT" or "BSB")
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return [], {}
        
        x, bmt_vars, bsb_vars = self.planning_model.get_variables()
        employees = self.planning_model.employees
        dates = self.planning_model.dates
        shift_codes = self.planning_model.shift_codes
        
        assignments = []
        assignment_id = 1
        
        # Extract regular shift assignments
        for emp in employees:
            for d in dates:
                for shift_code in shift_codes:
                    if (emp.id, d, shift_code) in x:
                        if self.solution.Value(x[(emp.id, d, shift_code)]) == 1:
                            # Find shift type ID
                            shift_type_id = None
                            for st in STANDARD_SHIFT_TYPES:
                                if st.code == shift_code:
                                    shift_type_id = st.id
                                    break
                            
                            assignment = ShiftAssignment(
                                id=assignment_id,
                                employee_id=emp.id,
                                shift_type_id=shift_type_id,
                                date=d,
                                is_springer_assignment=emp.is_springer
                            )
                            assignments.append(assignment)
                            assignment_id += 1
        
        # Extract special function assignments
        special_functions = {}
        
        for emp in employees:
            for d in dates:
                if (emp.id, d) in bmt_vars:
                    if self.solution.Value(bmt_vars[(emp.id, d)]) == 1:
                        special_functions[(emp.id, d)] = "BMT"
                        # Also create a shift assignment
                        assignment = ShiftAssignment(
                            id=assignment_id,
                            employee_id=emp.id,
                            shift_type_id=5,  # BMT shift type ID
                            date=d
                        )
                        assignments.append(assignment)
                        assignment_id += 1
                
                if (emp.id, d) in bsb_vars:
                    if self.solution.Value(bsb_vars[(emp.id, d)]) == 1:
                        special_functions[(emp.id, d)] = "BSB"
                        # Also create a shift assignment
                        assignment = ShiftAssignment(
                            id=assignment_id,
                            employee_id=emp.id,
                            shift_type_id=6,  # BSB shift type ID
                            date=d
                        )
                        assignments.append(assignment)
                        assignment_id += 1
        
        return assignments, special_functions
    
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
) -> Optional[Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str]]]:
    """
    Solve the shift planning problem.
    
    Args:
        planning_model: The shift planning model
        time_limit_seconds: Maximum time for solver
        num_workers: Number of parallel workers
        
    Returns:
        Tuple of (shift_assignments, special_functions) if solution found, None otherwise
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
    planning_model = create_shift_planning_model(employees, start, end, absences)
    planning_model.print_model_statistics()
    
    print("\nSolving...")
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if result:
        assignments, special_functions = result
        print(f"\n✓ Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - Special functions: {len(special_functions)}")
    else:
        print("\n✗ No solution found!")
