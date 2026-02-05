"""
Test for the rotation order constraint (F → N → S).
Verifies that employees cannot make invalid transitions between weeks.

Valid transitions:
- F → N (next in sequence)
- N → S (next in sequence)
- S → F (wrap around)
- Any shift can repeat (F → F, N → N, S → S)

Invalid transitions (should be penalized):
- F → S (skips N)
- N → F (skips S)
- S → N (skips F)
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
from ortools.sat.python import cp_model


def test_rotation_order_enforcement():
    """
    Test that the rotation order constraint correctly penalizes invalid transitions.
    """
    print("=" * 70)
    print("TEST: Rotation Order Enforcement (F → N → S)")
    print("=" * 70)
    
    # Create shift types
    shift_types = [
        ShiftType(id=1, code='F', name='Früh', start_time='05:45', end_time='13:45', 
                 hours=8.0, weekly_working_hours=48.0, 
                 min_staff_weekday=2, max_staff_weekday=10, 
                 min_staff_weekend=1, max_staff_weekend=10),
        ShiftType(id=2, code='S', name='Spät', start_time='13:45', end_time='21:45',
                 hours=8.0, weekly_working_hours=48.0,
                 min_staff_weekday=2, max_staff_weekday=10,
                 min_staff_weekend=1, max_staff_weekend=10),
        ShiftType(id=3, code='N', name='Nacht', start_time='21:45', end_time='05:45',
                 hours=8.0, weekly_working_hours=48.0,
                 min_staff_weekday=2, max_staff_weekday=10,
                 min_staff_weekend=1, max_staff_weekend=10),
    ]
    
    # Create teams - each team rotates through F → N → S
    teams = [
        Team(id=1, name='Team Alpha', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=2, name='Team Beta', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=3, name='Team Gamma', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create employees - 3 per team
    employees = []
    for team_id in [1, 2, 3]:
        for i in range(3):
            emp_id = (team_id - 1) * 3 + i + 1
            emp = Employee(
                id=emp_id,
                vorname=f'First{emp_id}',
                name=f'Last{emp_id}',
                personalnummer=f'PN{emp_id:03d}',
                team_id=team_id,
            )
            employees.append(emp)
    
    # Planning period: 4 weeks to test rotation
    # Use March 2026 as test period
    start_date = date(2026, 3, 2)  # Monday, Week 1
    end_date = date(2026, 3, 29)   # Sunday, Week 4 (4 full weeks)
    
    absences = []
    
    print("\nSetup:")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  Teams: {len(teams)} (Alpha, Beta, Gamma)")
    print(f"  Employees: {len(employees)} (3 per team)")
    print(f"  Expected rotation pattern:")
    print(f"    Week 1: Alpha=?, Beta=?, Gamma=?")
    print(f"    Week 2: Alpha=?, Beta=?, Gamma=?")
    print(f"    Week 3: Alpha=?, Beta=?, Gamma=?")
    print(f"    Week 4: Alpha=?, Beta=?, Gamma=?")
    
    # Create model
    try:
        planning_model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            shift_types=shift_types,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            locked_employee_shift={},
            locked_team_shift={}
        )
        
        print("\n✓ Planning model created successfully")
        
        # Create solver with short time limit for testing
        solver = ShiftPlanningSolver(
            planning_model=planning_model,
            time_limit_seconds=30,
            num_workers=4
        )
        
        print("✓ Solver created successfully")
        
        # Add all constraints
        print("\nAdding constraints...")
        solver.add_all_constraints()
        print("✓ All constraints added successfully")
        
        # Solve
        print("\nSolving...")
        success = solver.solve()
        
        if success and solver.solution:
            print("\n✓ Solution found!")
            
            # Get the solution object
            solution = solver.solution
            
            # Extract and display the schedule
            weeks = planning_model.weeks
            print("\nTeam Schedule:")
            for team in teams:
                print(f"\n{team.name} (ID={team.id}):")
                for week_idx, week_dates in enumerate(weeks):
                    monday = week_dates[0]
                    sunday = week_dates[-1]
                    # Find which shift this team has this week
                    team_shift_this_week = None
                    for shift_code in ['F', 'S', 'N']:
                        var = planning_model.team_shift.get((team.id, week_idx, shift_code))
                        if var is not None and solution.Value(var) == 1:
                            team_shift_this_week = shift_code
                            break
                    print(f"  Week {week_idx+1} ({monday} to {sunday}): {team_shift_this_week or 'NONE'}")
            
            # Verify rotation order for each team
            print("\nVerifying rotation order...")
            all_valid = True
            for team in teams:
                team_shifts = []
                for week_idx in range(len(weeks)):
                    for shift_code in ['F', 'S', 'N']:
                        var = planning_model.team_shift.get((team.id, week_idx, shift_code))
                        if var is not None and solution.Value(var) == 1:
                            team_shifts.append(shift_code)
                            break
                
                print(f"\n{team.name}: {' → '.join(team_shifts)}")
                
                # Check transitions
                for i in range(len(team_shifts) - 1):
                    from_shift = team_shifts[i]
                    to_shift = team_shifts[i + 1]
                    
                    # Define valid transitions
                    valid_next = {
                        'F': ['F', 'N'],
                        'N': ['N', 'S'],
                        'S': ['S', 'F']
                    }
                    
                    if to_shift in valid_next[from_shift]:
                        print(f"  ✓ Week {i+1}→{i+2}: {from_shift} → {to_shift} (valid)")
                    else:
                        print(f"  ✗ Week {i+1}→{i+2}: {from_shift} → {to_shift} (INVALID - breaks rotation order!)")
                        all_valid = False
            
            if all_valid:
                print("\n✅ SUCCESS: All transitions follow F → N → S rotation order!")
                return True
            else:
                print("\n❌ FAILURE: Some transitions violate the rotation order!")
                return False
        else:
            print("\n❌ No solution found!")
            print(f"   Status: {solver.status_name()}")
            return False
    
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_rotation_order_enforcement()
    exit(0 if success else 1)
