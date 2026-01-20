"""
Test to reproduce the INFEASIBLE solver issue when teams have wrong shift types configured.

This test sets allowed_shift_type_ids to ZD, BMT, BSB (not F, S, N) which would cause
the rotation constraint to be skipped, leading to INFEASIBLE.
"""

from datetime import date, timedelta
from entities import Employee, Team, Absence, STANDARD_SHIFT_TYPES
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_with_wrong_shifts():
    """
    Test with teams that have allowed_shift_type_ids set to ZD, BMT, BSB (NOT F, S, N).
    This should cause INFEASIBLE because rotation expects F, S, N.
    """
    # Find the shift type IDs for ZD, BMT, BSB (wrong shifts)
    zd_id = next(st.id for st in STANDARD_SHIFT_TYPES if st.code == "ZD")
    bmt_id = next(st.id for st in STANDARD_SHIFT_TYPES if st.code == "BMT")
    bsb_id = next(st.id for st in STANDARD_SHIFT_TYPES if st.code == "BSB")
    
    print(f"Wrong shift type IDs: ZD={zd_id}, BMT={bmt_id}, BSB={bsb_id}")
    
    # Create 3 teams with allowed_shift_type_ids set to WRONG shifts
    teams = [
        Team(id=1, name="Team 1", description="First team", allowed_shift_type_ids=[zd_id, bmt_id, bsb_id]),
        Team(id=2, name="Team 2", description="Second team", allowed_shift_type_ids=[zd_id, bmt_id, bsb_id]),
        Team(id=3, name="Team 3", description="Third team", allowed_shift_type_ids=[zd_id, bmt_id, bsb_id]),
    ]
    
    # Create employees: 3 teams × 5 members = 15 employees
    employees = []
    emp_id = 1
    for team_idx in range(3):
        team_id = team_idx + 1
        for member_idx in range(5):
            emp = Employee(
                id=emp_id,
                vorname=f"Employee{emp_id}",
                name=f"TeamMember{member_idx+1}",
                personalnummer=f"{team_id}{member_idx+1:02d}",
                team_id=team_id
            )
            employees.append(emp)
            emp_id += 1
    
    # Add 1 admin user without a team
    admin = Employee(
        id=emp_id,
        vorname="Admin",
        name="User",
        personalnummer="9999",
        team_id=None  # No team
    )
    employees.append(admin)
    
    print(f"Total employees: {len(employees)}")
    print(f"Employees in teams: {len([e for e in employees if e.team_id])}")
    print(f"Teams: {len(teams)}")
    for team in teams:
        print(f"  - {team.name}: {len([e for e in employees if e.team_id == team.id])} members, allowed_shift_type_ids={team.allowed_shift_type_ids}")
    
    # Planning period: 31 days
    start_date = date(2024, 1, 1)  # Start on a Monday
    end_date = start_date + timedelta(days=30)  # 31 days total
    
    print(f"\nPlanning period: {start_date} to {end_date} ({(end_date - start_date).days + 1} days)")
    
    # No absences for this test
    absences = []
    
    # Create model
    print("\nCreating model...")
    planning_model = ShiftPlanningModel(
        employees,
        teams,
        start_date,
        end_date,
        absences,
        shift_types=STANDARD_SHIFT_TYPES
    )
    
    # Create solver
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds=60)
    
    # Add constraints
    solver.add_all_constraints()
    
    # Solve
    print("\n" + "=" * 60)
    print("SOLVING...")
    print("=" * 60)
    result = solver.solve()
    
    # Check result
    print("\n" + "=" * 60)
    print("SOLVER RESULTS")
    print("=" * 60)
    
    if solver.status == cp_model.OPTIMAL:
        print(f"✓ OPTIMAL solution found!")
        return True
    elif solver.status == cp_model.FEASIBLE:
        print(f"⚠ FEASIBLE solution found (not optimal)")
        return True
    elif solver.status == cp_model.INFEASIBLE:
        print(f"✗ INFEASIBLE - No solution exists!")
        
        # Run diagnostics
        print("\n" + "=" * 60)
        print("DIAGNOSTICS")
        print("=" * 60)
        diagnostics = solver.diagnose_infeasibility()
        
        print(f"\nModel Configuration:")
        print(f"  - Total employees: {diagnostics['total_employees']}")
        print(f"  - Total teams: {diagnostics['total_teams']}")
        print(f"  - Planning days: {diagnostics['planning_days']}")
        print(f"  - Planning weeks: {diagnostics['planning_weeks']:.1f}")
        
        print(f"\nShift Staffing Analysis:")
        for shift_code, analysis in diagnostics['shift_analysis'].items():
            status = "✓" if analysis['is_feasible'] else "✗"
            print(f"  {status} {shift_code}: {analysis['eligible_employees']} eligible / {analysis['min_required']} required")
        
        print(f"\nTeam Configuration:")
        for team_name, info in diagnostics['team_analysis'].items():
            allowed = info['allowed_shifts'] if isinstance(info['allowed_shifts'], str) else f"{len(info['allowed_shifts'])} specific shifts"
            participates = "✓" if info['participates_in_rotation'] else "✗"
            print(f"  {participates} {team_name}: {info['size']} members, allowed shifts: {allowed}, participates_in_rotation={info['participates_in_rotation']}")
        
        if diagnostics['potential_issues']:
            print(f"\nPotential Issues:")
            for issue in diagnostics['potential_issues']:
                print(f"  - {issue}")
        
        return False
    else:
        print(f"? Unknown status: {solver.status}")
        return False


if __name__ == "__main__":
    from ortools.sat.python import cp_model
    success = test_with_wrong_shifts()
    print(f"\nTest result: {'PASS (expected INFEASIBLE)' if not success else 'FAIL (expected INFEASIBLE, got solution)'}")
    exit(0)  # Exit 0 regardless because we EXPECT this to fail
