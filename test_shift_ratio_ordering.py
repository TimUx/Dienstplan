"""
Test for shift ratio ordering based on max_staff capacity.

Problem from issue:
On Mo 2 (Monday, February 2), the solver assigned:
- N shift: 5 employees (max=3, OVERSTAFFED by 2)
- S shift: 5 employees (max=6, OK)
- F shift: 4 employees (max=8, UNDERSTAFFED by 4)

Expected: F should have the most workers, S medium, N the least (based on max_staff)

This test verifies that the daily shift ratio constraints enforce the proper ordering:
F >= S >= N on weekdays, based on their max_staff values.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_shift_ratio_ordering_respects_max_staff():
    """
    Test that shift worker counts follow max_staff ordering on weekdays.
    
    Scenario:
    - F shift: max 8 employees per day (highest capacity)
    - S shift: max 6 employees per day (medium capacity)
    - N shift: max 3 employees per day (lowest capacity)
    - Expected on each weekday: F_count >= S_count >= N_count
    - This prevents N from being overstaffed while F is understaffed
    """
    print("=" * 70)
    print("TEST: Shift Ratio Ordering Based on max_staff")
    print("=" * 70)
    
    # Create shift types matching the problem statement configuration
    shift_types = [
        ShiftType(
            id=1, code='F', name='Frühschicht', 
            start_time='05:45', end_time='13:45', 
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=4, max_staff_weekday=8,  # Highest capacity
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True,
            works_sunday=True,
            max_consecutive_days=6
        ),
        ShiftType(
            id=2, code='S', name='Spätschicht', 
            start_time='13:45', end_time='21:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=6,  # Medium capacity
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True,
            works_sunday=True,
            max_consecutive_days=6
        ),
        ShiftType(
            id=3, code='N', name='Nachtschicht', 
            start_time='21:45', end_time='05:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=3,  # Lowest capacity (exactly 3)
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True,
            works_sunday=True,
            max_consecutive_days=3
        )
    ]
    
    # Create 3 teams with 5 employees each = 15 total
    # This matches the scenario in the problem statement (3 teams)
    teams = [
        Team(id=1, name='Team Alpha'),
        Team(id=2, name='Team Beta'),
        Team(id=3, name='Team Gamma')
    ]
    
    # Create employees (5 per team, 15 total)
    employees = []
    for team_idx, team in enumerate(teams):
        for emp_idx in range(5):
            emp_id = team_idx * 5 + emp_idx + 1
            employees.append(
                Employee(
                    id=emp_id,
                    vorname=f"First{emp_id}",
                    name=f"Last{emp_id}",
                    personalnummer=f"PN{emp_id:03d}",
                    team_id=team.id
                )
            )
    
    # Plan for 4 weeks (Feb 2026) - starting from Monday Feb 2
    start_date = date(2026, 2, 2)  # Monday
    end_date = date(2026, 2, 28)   # Saturday
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Total employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    print(f"Shift types: F(max={shift_types[0].max_staff_weekday}), "
          f"S(max={shift_types[1].max_staff_weekday}), "
          f"N(max={shift_types[2].max_staff_weekday})")
    
    # Create planning model
    planning_model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        shift_types=shift_types,
        absences=[],
        locked_team_shift={},
        locked_employee_shift={}
    )
    
    # Create and run solver
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=120,
        num_workers=8
    )
    
    print("\nAdding constraints...")
    solver.add_all_constraints()
    
    print("Solving...")
    solver.solve()
    
    # Check if solution was found
    from ortools.sat.python.cp_model import CpSolverStatus
    if solver.status not in [CpSolverStatus.OPTIMAL, CpSolverStatus.FEASIBLE]:
        print(f"\n❌ FAILED: No feasible solution found (status: {solver.status})")
        return False
    
    print("\n✓ Solution found!")
    
    # Extract solution
    assignments, special_functions, complete_schedule = solver.extract_solution()
    
    
    # Extract and analyze shift assignments
    print("\nAnalyzing shift assignments by day...")
    
    violations = []
    
    # Check each weekday in the planning period
    current_date = start_date
    while current_date <= end_date:
        # Only check weekdays (Mon-Fri)
        if current_date.weekday() < 5:
            day_name = current_date.strftime("%A")
            
            # Count workers per shift on this day
            shift_counts = {'F': 0, 'S': 0, 'N': 0}
            
            for assignment in assignments:
                if assignment.date == current_date:
                    shift_code = None
                    for st in shift_types:
                        if st.id == assignment.shift_type_id:
                            shift_code = st.code
                            break
                    if shift_code in shift_counts:
                        shift_counts[shift_code] += 1
            
            f_count = shift_counts['F']
            s_count = shift_counts['S']
            n_count = shift_counts['N']
            
            print(f"\n{current_date} ({day_name}): F={f_count}, S={s_count}, N={n_count}")
            
            # Check expected ordering: F >= S >= N
            if s_count > f_count:
                violation_msg = f"  ⚠️  VIOLATION: S({s_count}) > F({f_count}) - S should not exceed F!"
                print(violation_msg)
                violations.append((current_date, violation_msg))
            
            if n_count > s_count:
                violation_msg = f"  ⚠️  VIOLATION: N({n_count}) > S({s_count}) - N should not exceed S!"
                print(violation_msg)
                violations.append((current_date, violation_msg))
            
            if n_count > f_count:
                violation_msg = f"  ⚠️  VIOLATION: N({n_count}) > F({f_count}) - N should not exceed F!"
                print(violation_msg)
                violations.append((current_date, violation_msg))
            
            # Check if ordering is correct
            if f_count >= s_count and s_count >= n_count:
                print(f"  ✓ Correct ordering: F >= S >= N")
        
        current_date += timedelta(days=1)
    
    # Report results
    print("\n" + "=" * 70)
    if violations:
        print(f"❌ TEST FAILED: {len(violations)} violations found")
        for viol_date, viol_msg in violations:
            print(f"  {viol_date}: {viol_msg}")
        return False
    else:
        print("✅ TEST PASSED: All weekdays respect F >= S >= N ordering")
        return True


if __name__ == "__main__":
    success = test_shift_ratio_ordering_respects_max_staff()
    exit(0 if success else 1)
