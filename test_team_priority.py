"""
Test for team priority in shift assignment.

Problem: When filling shifts to meet staffing requirements, the system should
prioritize using team members from the team assigned to that shift before
using cross-team members.

Example from problem statement:
- Sarah Hoffmann (PN008) from Team Beta was assigned F shift when her team had S shift
- Markus Richter (PN011) from Team Gamma was assigned S shift when his team had F shift
- These should have been reversed to keep teams together

The fix: Increase team_priority_violations weight to be higher than understaffing penalties.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_team_priority_in_shift_assignment():
    """
    Test that team members are prioritized over cross-team members when filling shifts.
    
    Scenario:
    - Week 2 has Team Beta assigned to S shift and Team Gamma assigned to F shift
    - Both shifts need to be filled to minimum staffing
    - The solver should use Team Beta members for S shift and Team Gamma members for F shift
    - NOT the reverse (which would be cross-team assignments)
    """
    print("=" * 70)
    print("TEST: Team Priority in Shift Assignment")
    print("=" * 70)
    
    # Create shift types with specific staffing requirements
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='06:00', end_time='14:30', 
            hours=8.5, 
            min_staff_weekday=2, max_staff_weekday=4,
            min_staff_weekend=1, max_staff_weekend=2
        ),
        ShiftType(
            id=2, code='S', name='Spät', 
            start_time='13:30', end_time='22:00',
            hours=8.5, 
            min_staff_weekday=2, max_staff_weekday=4,
            min_staff_weekend=1, max_staff_weekend=2
        ),
        ShiftType(
            id=3, code='N', name='Nacht', 
            start_time='21:30', end_time='06:30',
            hours=9, 
            min_staff_weekday=1, max_staff_weekday=2,
            min_staff_weekend=1, max_staff_weekend=2
        ),
        ShiftType(id=4, code='+', name='Frei', start_time=None, end_time=None, hours=0),
    ]
    
    # Create teams - just 2 teams for simplicity
    teams = [
        Team(id=2, name='Beta', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=3, name='Gamma', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create employees - 5 per team, enough to fill shifts and meet hours
    employees = []
    
    # Team Beta (5 employees) - Sarah Hoffmann is one of them
    for i in range(5):
        emp = Employee(
            id=i + 1,
            vorname='Sarah' if i == 0 else f'BetaFirst{i+1}',
            name='Hoffmann' if i == 0 else f'BetaLast{i+1}',
            personalnummer='PN008' if i == 0 else f'PN10{i+1}',
            team_id=2
        )
        employees.append(emp)
    
    # Team Gamma (5 employees) - Markus Richter is one of them
    for i in range(5):
        emp = Employee(
            id=i + 6,
            vorname='Markus' if i == 0 else f'GammaFirst{i+1}',
            name='Richter' if i == 0 else f'GammaLast{i+1}',
            personalnummer='PN011' if i == 0 else f'PN20{i+1}',
            team_id=3
        )
        employees.append(emp)
    
    # Planning period: 4 weeks in February 2026 (standard monthly planning)
    start_date = date(2026, 2, 2)  # Monday
    end_date = date(2026, 3, 1)   # Sunday (4 full weeks)
    
    # Create model
    model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        shift_types=shift_types,
        start_date=start_date,
        end_date=end_date,
        absences=[],
        locked_team_shift={
            # Week 0-1: Establish rotation
            (2, 0): 'F',  # Team Beta gets F shift
            (3, 0): 'S',  # Team Gamma gets S shift
            (2, 1): 'N',  # Team Beta gets N shift
            (3, 1): 'F',  # Team Gamma gets F shift
            # Week 2 (Feb 16-22): CRITICAL TEST - Beta=S, Gamma=F
            (2, 2): 'S',  # Team Beta should work S shift
            (3, 2): 'F',  # Team Gamma should work F shift (NOT S!)
            # Week 3: Continue rotation
            (2, 3): 'F',
            (3, 3): 'N',
        },
        locked_employee_shift={}
    )
    
    # Create and run solver
    solver = ShiftPlanningSolver(model, time_limit_seconds=60)
    solver.add_all_constraints()
    
    print("\nRunning solver...")
    solver.solve()
    
    # Check if we have a solution (FEASIBLE or OPTIMAL)
    from ortools.sat.python.cp_model import CpSolverStatus
    if solver.status not in [CpSolverStatus.OPTIMAL, CpSolverStatus.FEASIBLE]:
        print(f"\n❌ FAIL: Solver did not find a solution (status: {solver.status})")
        return False
    
    print(f"\n✓ Solver found solution (status: {solver.status})")
    
    # Extract solution
    shift_assignments, complete_schedule = solver.extract_solution()
    
    # Analyze Week 2 (Feb 16-22) assignments - THE CRITICAL WEEK
    print("\n" + "=" * 70)
    print("Week 2 Analysis (Feb 16-22) - CRITICAL TEST WEEK:")
    print("=" * 70)
    print("Expected: Team Beta works S shift, Team Gamma works F shift")
    print()
    
    week_start = date(2026, 2, 16)  # Week 2 starts Feb 16
    week_end = date(2026, 2, 22)    # Week 2 ends Feb 22
    
    # Count cross-team assignments in the week
    cross_team_violations = []
    
    # Helper to get shift code from shift_type_id
    shift_type_map = {st.id: st.code for st in shift_types}
    
    for emp in employees:
        emp_team = next((t for t in teams if t.id == emp.team_id), None)
        emp_assignments = [
            a for a in shift_assignments 
            if a.employee_id == emp.id 
            and week_start <= a.date <= week_end
            and shift_type_map.get(a.shift_type_id) in ['F', 'S', 'N']
        ]
        
        for assignment in emp_assignments:
            shift_code = shift_type_map.get(assignment.shift_type_id)
            
            # Determine which team has this shift in week 2
            expected_team_for_shift = None
            if shift_code == 'F':
                expected_team_for_shift = 3  # Gamma has F in week 2
            elif shift_code == 'S':
                expected_team_for_shift = 2  # Beta has S in week 2
            elif shift_code == 'N':
                # No team has N shift in week 2, so cross-team is necessary
                expected_team_for_shift = None
            
            # Only flag violations for F and S shifts (where teams are assigned)
            if expected_team_for_shift and emp.team_id != expected_team_for_shift:
                cross_team_violations.append({
                    'employee': f"{emp.vorname} {emp.name} ({emp.personalnummer})",
                    'team': emp_team.name if emp_team else 'Unknown',
                    'shift': shift_code,
                    'date': assignment.date,
                    'expected_team_id': expected_team_for_shift
                })
                print(f"\n⚠ Cross-team assignment detected:")
                print(f"   Employee: {emp.vorname} {emp.name} ({emp.personalnummer})")
                print(f"   Team: {emp_team.name if emp_team else 'Unknown'}")
                print(f"   Assigned: {shift_code} shift on {assignment.date}")
                print(f"   Expected: Team {expected_team_for_shift} to work {shift_code} shift")
    
    # Check specific employees from problem statement
    sarah_hoffmann = next((e for e in employees if e.personalnummer == 'PN008'), None)
    markus_richter = next((e for e in employees if e.personalnummer == 'PN011'), None)
    
    if sarah_hoffmann:
        sarah_week = [
            a for a in shift_assignments 
            if a.employee_id == sarah_hoffmann.id 
            and week_start <= a.date <= week_end
            and shift_type_map.get(a.shift_type_id) in ['F', 'S', 'N']
        ]
        print(f"\nSarah Hoffmann (PN008) - Team Beta - Week assignments:")
        for a in sarah_week:
            shift_code = shift_type_map.get(a.shift_type_id)
            print(f"  {a.date}: {shift_code}")
        
        # Check if Sarah has any F shifts (would be wrong - she's Team Beta, should be S)
        sarah_f_shifts = [a for a in sarah_week if shift_type_map.get(a.shift_type_id) == 'F']
        if sarah_f_shifts:
            print(f"  ❌ ERROR: Sarah has {len(sarah_f_shifts)} F shift(s) but her team has S shift!")
    
    if markus_richter:
        markus_week = [
            a for a in shift_assignments 
            if a.employee_id == markus_richter.id 
            and week_start <= a.date <= week_end
            and shift_type_map.get(a.shift_type_id) in ['F', 'S', 'N']
        ]
        print(f"\nMarkus Richter (PN011) - Team Gamma - Week assignments:")
        for a in markus_week:
            shift_code = shift_type_map.get(a.shift_type_id)
            print(f"  {a.date}: {shift_code}")
        
        # Check if Markus has any S shifts (would be wrong - he's Team Gamma, should be F)
        markus_s_shifts = [a for a in markus_week if shift_type_map.get(a.shift_type_id) == 'S']
        if markus_s_shifts:
            print(f"  ❌ ERROR: Markus has {len(markus_s_shifts)} S shift(s) but his team has F shift!")
    
    # Test result
    print("\n" + "=" * 70)
    print("TEST RESULT:")
    print("=" * 70)
    
    if len(cross_team_violations) == 0:
        print("✓ PASS: No cross-team violations detected")
        print("  Teams are properly prioritized over cross-team assignments")
        return True
    else:
        print(f"❌ FAIL: {len(cross_team_violations)} cross-team violation(s) detected")
        print("  Team members should be used before cross-team members")
        return False


if __name__ == '__main__':
    success = test_team_priority_in_shift_assignment()
    exit(0 if success else 1)
