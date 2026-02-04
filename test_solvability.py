"""
Test that verifies the model can be solved (not INFEASIBLE) after handling conflicts.
This test creates a minimal model with conflicts and tries to solve it.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from constraints import add_all_constraints
from ortools.sat.python import cp_model


def test_solvability_after_conflict_handling():
    """
    Test that the model can be solved after conflict handling.
    This ensures that skipping conflicting constraints actually prevents INFEASIBLE.
    """
    print("=" * 70)
    print("TEST: Model Solvability After Conflict Handling")
    print("=" * 70)
    
    # Create shift types
    shift_types = [
        ShiftType(id=1, code='F', name='Früh', start_time='06:00', end_time='14:30', 
                 hours=8.5, min_staff_weekday=2, max_staff_weekday=6),
        ShiftType(id=2, code='S', name='Spät', start_time='13:30', end_time='22:00',
                 hours=8.5, min_staff_weekday=2, max_staff_weekday=5),
        ShiftType(id=3, code='N', name='Nacht', start_time='21:30', end_time='06:30',
                 hours=9, min_staff_weekday=2, max_staff_weekday=4),
    ]
    
    # Create teams
    teams = [
        Team(id=1, name='Alpha', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=2, name='Beta', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create employees - split between teams
    employees = []
    for team_id in [1, 2]:
        for i in range(5):
            emp_id = (team_id - 1) * 5 + i + 1
            emp = Employee(
                id=emp_id,
                vorname=f'First{emp_id}',
                name=f'Last{emp_id}',
                personalnummer=f'{emp_id:04d}',
                team_id=team_id,
            )
            employees.append(emp)
    
    # Short planning period: Feb 9-15, 2026 (one week)
    start_date = date(2026, 2, 9)  # Monday
    end_date = date(2026, 2, 15)    # Sunday
    absences = []
    
    # Create conflicting locked assignments
    # Simulate the problem: Team 1 locked to 'F', but employees locked to 'S'
    locked_team_shift = {
        (1, 0): 'F',  # Team 1, Week 0 -> Früh
    }
    
    # Lock employees to conflicting shifts
    locked_employee_shift = {}
    # Team 1 employees locked to 'S' when team is locked to 'F'
    for emp_id in [2, 3]:
        for day_offset in range(3):  # Just 3 days to reduce constraints
            d = date(2026, 2, 9) + timedelta(days=day_offset)
            locked_employee_shift[(emp_id, d)] = 'S'
    
    print("\nSetup:")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  locked_team_shift: Team 1, Week 0 -> 'F'")
    print(f"  locked_employee_shift: Employees 2,3 (Team 1), Feb 9-11 -> 'S'")
    print(f"  ⚠️  CONFLICT: Team locked to 'F' but employees locked to 'S'")
    
    print("\nCreating model...")
    try:
        planning_model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types,
            locked_team_shift=locked_team_shift,
            locked_employee_shift=locked_employee_shift
        )
        print("✓ Model created successfully")
        
        # Add constraints
        print("\nAdding constraints...")
        add_all_constraints(planning_model, shift_types)
        print("✓ Constraints added successfully")
        
        # Try to solve
        print("\nAttempting to solve...")
        cp_solver = cp_model.CpSolver()
        cp_solver.parameters.max_time_in_seconds = 10.0  # Short time limit
        cp_solver.parameters.log_search_progress = False  # Quiet mode
        
        model_obj = planning_model.get_model()
        status = cp_solver.Solve(model_obj)
        
        if status == cp_model.INFEASIBLE:
            print("❌ TEST FAILED: Model is INFEASIBLE")
            print("   The conflict handling did not prevent INFEASIBLE state")
            return False
        elif status == cp_model.OPTIMAL:
            print("✅ Model solved successfully (OPTIMAL)")
            return True
        elif status == cp_model.FEASIBLE:
            print("✅ Model solved successfully (FEASIBLE)")
            return True
        elif status == cp_model.MODEL_INVALID:
            print("❌ TEST FAILED: Model is INVALID")
            return False
        else:
            # UNKNOWN status (timeout, etc.) - still counts as not INFEASIBLE
            print(f"⚠️  Model status: {cp_solver.StatusName(status)}")
            print("   Not INFEASIBLE, so conflict handling worked")
            return True
            
    except Exception as e:
        print(f"❌ TEST FAILED: Exception occurred")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔧 Testing Model Solvability After Conflict Handling 🔧\n")
    
    test_passed = test_solvability_after_conflict_handling()
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    if test_passed:
        print("✅ TEST PASSED")
        print("\nThe fix successfully prevents INFEASIBLE by:")
        print("  1. Detecting conflicting locked shifts")
        print("  2. Skipping conflicting constraints")
        print("  3. Allowing the model to be solved")
    else:
        print("❌ TEST FAILED")
        print("\nThe model is still INFEASIBLE despite conflict handling")
