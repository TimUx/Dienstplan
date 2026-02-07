"""
Test for daily shift ratio constraint (F >= S on weekdays).

This test verifies that on each weekday (Mon-Fri), F shifts have at least
as many workers as S shifts, enforcing the capacity ratio from max_staff settings.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_daily_f_greater_equal_s():
    """
    Test that F >= S on each weekday.
    
    Scenario:
    - F shift: max 8 employees per day
    - S shift: max 6 employees per day
    - On each weekday, count(F) should be >= count(S)
    """
    print("=" * 70)
    print("TEST: Daily F >= S Constraint on Weekdays")
    print("=" * 70)
    
    # Create shift types
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='06:00', end_time='14:00', 
            hours=8.0, 
            min_staff_weekday=4, max_staff_weekday=8,
            min_staff_weekend=2, max_staff_weekend=4
        ),
        ShiftType(
            id=2, code='S', name='Spät', 
            start_time='14:00', end_time='22:00',
            hours=8.0, 
            min_staff_weekday=3, max_staff_weekday=6,
            min_staff_weekend=2, max_staff_weekend=3
        ),
        ShiftType(
            id=3, code='N', name='Nacht', 
            start_time='22:00', end_time='06:00',
            hours=8.0, 
            min_staff_weekday=2, max_staff_weekday=4,
            min_staff_weekend=1, max_staff_weekend=2
        )
    ]
    
    # Create 3 teams with 5 employees each = 15 total
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
    
    # Plan for 4 weeks (Feb 2026)
    start_date = date(2026, 2, 2)  # Monday
    end_date = date(2026, 2, 28)   # Saturday (4 full weeks)
    
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
    
    # Add all constraints
    solver.add_all_constraints()
    
    # Solve
    solver.solve()
    
    # Check if solution was found
    from ortools.sat.python.cp_model import CpSolverStatus
    if solver.status not in [CpSolverStatus.OPTIMAL, CpSolverStatus.FEASIBLE]:
        print(f"❌ FAIL: No feasible solution found (status: {solver.status})")
        return False
    
    print("\n✓ Solver found solution")
    
    # Extract solution
    assignments, complete_schedule = solver.extract_solution()
    
    # Create shift_type_id to code mapping
    shift_type_map = {st.id: st.code for st in shift_types}
    
    # Count shifts per day
    daily_counts = {}
    for assignment in assignments:
        d = assignment.date
        if d not in daily_counts:
            daily_counts[d] = {'F': 0, 'S': 0, 'N': 0}
        shift_code = shift_type_map.get(assignment.shift_type_id, '?')
        if shift_code in daily_counts[d]:
            daily_counts[d][shift_code] += 1
    
    # Check F >= S for weekdays
    violations = []
    print("\n" + "=" * 70)
    print("Daily Shift Counts (Weekdays Only):")
    print("=" * 70)
    print(f"{'Date':<12} {'Day':<4} {'F':>3} {'S':>3} {'N':>3} {'Status':<20}")
    print("-" * 70)
    
    for d in sorted(daily_counts.keys()):
        if d.weekday() >= 5:  # Skip weekends
            continue
        
        counts = daily_counts[d]
        f_count = counts['F']
        s_count = counts['S']
        n_count = counts['N']
        
        weekday_name = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d.weekday()]
        
        if s_count > f_count:
            status = f"❌ VIOLATION: S > F"
            violations.append((d, f_count, s_count))
        elif s_count == f_count and f_count > 0:
            status = f"⚠️  S == F (edge case)"
        else:
            status = f"✓ OK: F >= S"
        
        print(f"{d.isoformat():<12} {weekday_name:<4} {f_count:>3} {s_count:>3} {n_count:>3} {status:<20}")
    
    print("=" * 70)
    
    if violations:
        print(f"\n❌ FAIL: Found {len(violations)} violations where S > F on weekdays:")
        for d, f_count, s_count in violations:
            print(f"  - {d.isoformat()}: F={f_count}, S={s_count} (difference: {s_count - f_count})")
        return False
    else:
        print("\n✓ PASS: All weekdays satisfy F >= S constraint")
        print("  The daily shift ratio constraint is working correctly!")
        return True


if __name__ == "__main__":
    success = test_daily_f_greater_equal_s()
    exit(0 if success else 1)
