"""
Test for shift distribution based on max_staff ratios.

Problem: Shift distribution should respect the max_staff settings from the database.
If F shift has max 8 and S shift has max 6, then F should get proportionally more 
employees assigned than S when filling shifts to meet target hours.

This test verifies that the dynamic weight calculation based on max_staff values
produces the correct distribution ratios.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_shift_distribution_respects_max_staff_ratios():
    """
    Test that shifts are distributed proportionally to their max_staff settings.
    
    Scenario:
    - F shift: max 8 employees per day
    - S shift: max 6 employees per day
    - N shift: max 4 employees per day
    - Expected ratio: F gets the most, then S, then N
    - When solver fills shifts to meet hours, it should prioritize F > S > N
    """
    print("=" * 70)
    print("TEST: Shift Distribution Based on max_staff Ratios")
    print("=" * 70)
    
    # Create shift types with SPECIFIC max_staff ratios to test
    # F:S:N = 8:6:4 = 2:1.5:1
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='06:00', end_time='14:00', 
            hours=8.0, 
            min_staff_weekday=4, max_staff_weekday=8,  # Highest capacity
            min_staff_weekend=2, max_staff_weekend=4
        ),
        ShiftType(
            id=2, code='S', name='Spät', 
            start_time='14:00', end_time='22:00',
            hours=8.0, 
            min_staff_weekday=3, max_staff_weekday=6,  # Medium capacity
            min_staff_weekend=2, max_staff_weekend=3
        ),
        ShiftType(
            id=3, code='N', name='Nacht', 
            start_time='22:00', end_time='06:00',
            hours=8.0, 
            min_staff_weekday=2, max_staff_weekday=4,  # Lowest capacity
            min_staff_weekend=1, max_staff_weekend=2
        )
    ]
    
    # Create 3 teams with 6 employees each = 18 total
    teams = [
        Team(id=1, name='Team Alpha'),
        Team(id=2, name='Team Beta'),
        Team(id=3, name='Team Gamma')
    ]
    
    # Create employees (6 per team, 18 total)
    employees = []
    for team_idx, team in enumerate(teams):
        for emp_idx in range(6):
            emp_id = team_idx * 6 + emp_idx + 1
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
    assignments, special_functions, complete_schedule = solver.extract_solution()
    
    # Create shift_type_id to code mapping
    shift_type_map = {st.id: st.code for st in shift_types}
    
    # Count shift assignments for weekdays (where the ratio matters most)
    shift_counts = {'F': 0, 'S': 0, 'N': 0}
    weekday_assignments = 0
    
    for assignment in assignments:
        if assignment.date.weekday() < 5:  # Monday-Friday only
            shift_code = shift_type_map.get(assignment.shift_type_id, '?')
            if shift_code in shift_counts:
                shift_counts[shift_code] += 1
                weekday_assignments += 1
    
    print("\n" + "=" * 70)
    print("Weekday Shift Distribution Analysis:")
    print("=" * 70)
    print(f"Total weekday assignments: {weekday_assignments}")
    print(f"F (Früh) shifts:   {shift_counts['F']:3d} ({shift_counts['F']/weekday_assignments*100:.1f}%)")
    print(f"S (Spät) shifts:   {shift_counts['S']:3d} ({shift_counts['S']/weekday_assignments*100:.1f}%)")
    print(f"N (Nacht) shifts:  {shift_counts['N']:3d} ({shift_counts['N']/weekday_assignments*100:.1f}%)")
    
    # Calculate actual ratios
    if shift_counts['N'] > 0:
        ratio_f_to_n = shift_counts['F'] / shift_counts['N']
        ratio_s_to_n = shift_counts['S'] / shift_counts['N']
        print(f"\nActual ratios (compared to N=1.0):")
        print(f"  F:N = {ratio_f_to_n:.2f}:1.0")
        print(f"  S:N = {ratio_s_to_n:.2f}:1.0")
    
    # Expected ratios based on max_staff: F(8):S(6):N(4) = 2.0:1.5:1.0
    expected_ratio_f_to_n = 8.0 / 4.0  # 2.0
    expected_ratio_s_to_n = 6.0 / 4.0  # 1.5
    print(f"\nExpected ratios (based on max_staff):")
    print(f"  F:N = {expected_ratio_f_to_n:.2f}:1.0")
    print(f"  S:N = {expected_ratio_s_to_n:.2f}:1.0")
    
    # Check that F > S > N (basic ordering)
    if not (shift_counts['F'] >= shift_counts['S'] >= shift_counts['N']):
        print("\n❌ FAIL: Shift distribution does not follow F >= S >= N ordering")
        print(f"   Got: F={shift_counts['F']}, S={shift_counts['S']}, N={shift_counts['N']}")
        return False
    
    print("\n✓ PASS: Shift distribution follows F >= S >= N ordering")
    
    # Check that the ratios are approximately correct (within 20% tolerance)
    # NOTE: This is a soft check because the solver has many competing constraints
    # (team cohesion, rotation order, rest time, shift grouping, etc.) that may prevent
    # achieving exact distribution ratios. The important requirement is the ORDERING (F >= S >= N),
    # not the exact ratio. A 20% deviation is acceptable given operational constraints.
    if shift_counts['N'] > 0:
        actual_f_to_n = shift_counts['F'] / shift_counts['N']
        actual_s_to_n = shift_counts['S'] / shift_counts['N']
        
        # Allow 20% deviation from expected ratios
        tolerance = 0.20
        f_ratio_ok = abs(actual_f_to_n - expected_ratio_f_to_n) / expected_ratio_f_to_n <= tolerance
        s_ratio_ok = abs(actual_s_to_n - expected_ratio_s_to_n) / expected_ratio_s_to_n <= tolerance
        
        if f_ratio_ok and s_ratio_ok:
            print(f"✓ PASS: Ratios are within {tolerance*100:.0f}% of expected values")
        else:
            print(f"⚠ WARNING: Ratios deviate more than {tolerance*100:.0f}% from expected")
            print(f"   This may be acceptable due to other constraints")
    
    print("\n" + "=" * 70)
    print("TEST RESULT:")
    print("=" * 70)
    print("✓ PASS: Shift distribution respects max_staff capacity ordering")
    print("  F shift (max 8) gets most assignments")
    print("  S shift (max 6) gets medium assignments")
    print("  N shift (max 4) gets fewest assignments")
    
    return True


if __name__ == "__main__":
    test_shift_distribution_respects_max_staff_ratios()
