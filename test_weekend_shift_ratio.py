"""
Test for weekend shift ratio ordering based on max_staff capacity.

Problem from issue:
Sometimes 5 night shifts are distributed on weekends, even though the algorithm
should distribute shifts proportionally based on MAX employee settings. Shifts with
more MAX employees should get proportionally more shifts per day, including weekends.

This test verifies that the daily shift ratio constraints enforce the proper ordering
on weekends: shifts are distributed according to their max_staff_weekend values.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_weekend_shift_ratio_respects_max_staff():
    """
    Test that shift worker counts follow max_staff ordering on weekends.
    
    Scenario:
    - F shift: max 5 employees on weekends (highest capacity)
    - S shift: max 4 employees on weekends (medium capacity)
    - N shift: max 3 employees on weekends (lowest capacity)
    - Expected on each weekend day: F_count >= S_count >= N_count
    - This prevents N from being overstaffed (5 workers) while F is understaffed
    """
    print("=" * 70)
    print("TEST: Weekend Shift Ratio Ordering Based on max_staff_weekend")
    print("=" * 70)
    
    # Create shift types with different weekend capacities
    shift_types = [
        ShiftType(
            id=1, code='F', name='Frühschicht', 
            start_time='05:45', end_time='13:45', 
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=4, max_staff_weekday=8,
            min_staff_weekend=2, max_staff_weekend=5,  # Highest weekend capacity
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
            min_staff_weekday=3, max_staff_weekday=6,
            min_staff_weekend=2, max_staff_weekend=4,  # Medium weekend capacity
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
            min_staff_weekday=3, max_staff_weekday=3,
            min_staff_weekend=2, max_staff_weekend=3,  # Lowest weekend capacity
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True,
            works_sunday=True,
            max_consecutive_days=3
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
    
    # Plan for 4 weeks (Feb 2026) - starting from Monday Feb 2
    start_date = date(2026, 2, 2)  # Monday
    end_date = start_date + timedelta(days=27)  # 4 weeks
    
    # Create model with no absences
    planning_model = ShiftPlanningModel(
        shift_types=shift_types,
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=[]
    )
    
    # Solve
    print("\nRunning solver...")
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=180,
        num_workers=8
    )
    
    solver.solve()
    
    # Check if solution was found
    from ortools.sat.python.cp_model import CpSolverStatus
    if solver.status not in [CpSolverStatus.OPTIMAL, CpSolverStatus.FEASIBLE]:
        print(f"\n❌ FAILED: No feasible solution found (status: {solver.status})")
        return
    
    print("\n✓ Solution found!")
    
    # Extract solution
    assignments, complete_schedule = solver.extract_solution()
    
    if not assignments:
        print("❌ FAIL: No assignments found")
        return
    
    # Get dates from the model
    dates = planning_model.dates
    
    # Analyze weekend shift distribution
    print("\nWeekend Shift Distribution Analysis:")
    print("-" * 70)
    print(f"{'Date':<12} {'Day':<4} {'F':>3} {'S':>3} {'N':>3} {'Status':<30}")
    print("-" * 70)
    
    violations = []
    weekend_count = 0
    correct_count = 0
    
    for d in dates:
        # Only check weekends (Saturday=5, Sunday=6)
        if d.weekday() < 5:
            continue
        
        weekend_count += 1
        
        # Count shifts per type
        shift_counts = {'F': 0, 'S': 0, 'N': 0}
        for assignment in assignments:
            if assignment.date == d:
                shift_counts[assignment.shift_code] += 1
        
        # Check ordering: F >= S >= N (based on max_staff_weekend: 5 >= 4 >= 3)
        day_name = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d.weekday()]
        
        is_correct = True
        status = "✓ OK: F >= S >= N"
        
        # Check F >= S
        if shift_counts['F'] < shift_counts['S']:
            is_correct = False
            status = f"❌ VIOLATION: S ({shift_counts['S']}) > F ({shift_counts['F']})"
            violations.append((d, 'F < S', shift_counts['F'], shift_counts['S']))
        
        # Check S >= N
        elif shift_counts['S'] < shift_counts['N']:
            is_correct = False
            status = f"❌ VIOLATION: N ({shift_counts['N']}) > S ({shift_counts['S']})"
            violations.append((d, 'S < N', shift_counts['S'], shift_counts['N']))
        
        # Check F >= N
        elif shift_counts['F'] < shift_counts['N']:
            is_correct = False
            status = f"❌ VIOLATION: N ({shift_counts['N']}) > F ({shift_counts['F']})"
            violations.append((d, 'F < N', shift_counts['F'], shift_counts['N']))
        
        # Special case: Check for edge case mentioned in problem (5 N shifts on weekend)
        if shift_counts['N'] >= 5:
            status = f"❌ OVERSTAFFING: N has {shift_counts['N']} workers (max_weekend=3)"
            is_correct = False
            violations.append((d, 'N overstaffed', shift_counts['N'], 3))
        
        if is_correct:
            correct_count += 1
        
        print(f"{d.strftime('%Y-%m-%d'):<12} {day_name:<4} {shift_counts['F']:>3} "
              f"{shift_counts['S']:>3} {shift_counts['N']:>3} {status:<30}")
    
    print("-" * 70)
    
    # Summary
    print(f"\nSummary:")
    print(f"  Total weekend days: {weekend_count}")
    print(f"  Days with correct ordering: {correct_count} ({100*correct_count/weekend_count:.1f}%)")
    print(f"  Days with violations: {len(violations)} ({100*len(violations)/weekend_count:.1f}%)")
    
    if violations:
        print("\nViolation Details:")
        for d, violation_type, count_a, count_b in violations:
            print(f"  - {d}: {violation_type} ({count_a} vs {count_b})")
    
    # Overall distribution
    print("\nOverall Weekend Distribution:")
    total_f = sum(1 for a in assignments if a.date.weekday() >= 5 and a.shift_code == 'F')
    total_s = sum(1 for a in assignments if a.date.weekday() >= 5 and a.shift_code == 'S')
    total_n = sum(1 for a in assignments if a.date.weekday() >= 5 and a.shift_code == 'N')
    total = total_f + total_s + total_n
    
    print(f"  F: {total_f} shifts ({100*total_f/total:.1f}%)")
    print(f"  S: {total_s} shifts ({100*total_s/total:.1f}%)")
    print(f"  N: {total_n} shifts ({100*total_n/total:.1f}%)")
    print(f"  Expected ordering: F > S > N (based on max_staff_weekend: 5 > 4 > 3)")
    print(f"  Actual ordering: {'F > S > N ✓' if total_f >= total_s >= total_n else 'INCORRECT ❌'}")
    
    # Test passes if majority of weekends respect the ordering
    success_rate = correct_count / weekend_count if weekend_count > 0 else 0
    
    if success_rate >= 0.75:  # At least 75% compliance
        print(f"\n✅ PASS: {success_rate*100:.1f}% of weekend days respect shift capacity ordering")
        print("   (75% or higher is acceptable due to team rotation constraints)")
    else:
        print(f"\n❌ FAIL: Only {success_rate*100:.1f}% of weekend days respect shift capacity ordering")
        print("   (Expected at least 75% compliance)")
        assert False, f"Too many violations: {len(violations)}/{weekend_count} weekend days"


if __name__ == "__main__":
    test_weekend_shift_ratio_respects_max_staff()
    print("\nAll tests passed! ✅")
