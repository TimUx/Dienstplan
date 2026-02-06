#!/usr/bin/env python3
"""
Comprehensive test demonstrating the cross-team override fix with a realistic scenario.
This test creates a setup similar to the February 2026 problem reported by the user.
"""

import sys
sys.path.insert(0, '/home/runner/work/Dienstplan/Dienstplan')

from datetime import date
from entities import Employee, Team, ShiftType, STANDARD_SHIFT_TYPES
from model import ShiftPlanningModel  
from solver import solve_shift_planning

def test_february_2026_realistic_scenario():
    """
    Test the complete February 2026 scenario with proper team distribution.
    Ensures that all team members follow their team's rotation pattern.
    """
    
    print("="*80)
    print("FEBRUARY 2026 REALISTIC SCENARIO TEST")
    print("="*80)
    print()
    print("This test verifies that the cross-team override fix works correctly")
    print("in a realistic scenario with 3 teams and 15 employees.")
    print()
    
    # Create 3 teams with rotation group
    teams = [
        Team(id=1, name="Team Alpha", description="Erste Schichtgruppe", rotation_group_id=1),
        Team(id=2, name="Team Beta", description="Zweite Schichtgruppe", rotation_group_id=1),
        Team(id=3, name="Team Gamma", description="Dritte Schichtgruppe", rotation_group_id=1),
    ]
    
    # Create 15 employees distributed across 3 teams (5 per team)
    employees = [
        # Team Alpha
        Employee(id=1, name="Schmidt", vorname="Anna", personalnummer="PN002", team_id=1),
        Employee(id=2, name="Franke", vorname="Robert", personalnummer="S001", team_id=1),
        Employee(id=3, name="Meyer", vorname="Lisa", personalnummer="PN004", team_id=1),
        Employee(id=4, name="Müller", vorname="Max", personalnummer="PN001", team_id=1),
        Employee(id=5, name="Weber", vorname="Peter", personalnummer="PN003", team_id=1),
        
        # Team Beta
        Employee(id=6, name="Koch", vorname="Daniel", personalnummer="PN009", team_id=2),
        Employee(id=7, name="Becker", vorname="Julia", personalnummer="PN006", team_id=2),
        Employee(id=8, name="Schulz", vorname="Michael", personalnummer="PN007", team_id=2),
        Employee(id=9, name="Hoffmann", vorname="Sarah", personalnummer="PN008", team_id=2),
        Employee(id=10, name="Zimmermann", vorname="Thomas", personalnummer="S002", team_id=2),
        
        # Team Gamma
        Employee(id=11, name="Wolf", vorname="Andreas", personalnummer="PN013", team_id=3),
        Employee(id=12, name="Lange", vorname="Maria", personalnummer="S003", team_id=3),
        Employee(id=13, name="Richter", vorname="Markus", personalnummer="PN011", team_id=3),
        Employee(id=14, name="Schröder", vorname="Nicole", personalnummer="PN014", team_id=3),
        Employee(id=15, name="Klein", vorname="Stefanie", personalnummer="PN012", team_id=3),
    ]
    
    # Use standard shift types
    shift_types = STANDARD_SHIFT_TYPES
    
    # Plan for February 2026
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 28)
    
    print(f"Planning Period: {start_date} to {end_date}")
    print(f"Teams: {len(teams)}")
    print(f"Employees: {len(employees)}")
    print()
    
    # Expected team rotations based on ISO week numbers
    print("Expected Team Rotations (F→N→S pattern):")
    print("  ISO Week 7 (Feb 9-15):   Team Alpha=N, Team Beta=S, Team Gamma=F")
    print("  ISO Week 8 (Feb 16-22):  Team Alpha=S, Team Beta=F, Team Gamma=N")
    print("  ISO Week 9 (Feb 23-Mar): Team Alpha=F, Team Beta=N, Team Gamma=S")
    print()
    print("Key Test: Team Alpha should have F (not S) during Feb 23-27")
    print()
    
    # Create planning model
    planning_model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=[],
        shift_types=shift_types
    )
    
    # Solve
    print("Solving shift planning problem...")
    print("(This may take 1-2 minutes)")
    print()
    
    result = solve_shift_planning(
        planning_model=planning_model,
        time_limit_seconds=120,
        num_workers=4
    )
    
    if not result:
        print("❌ FAILURE: No solution found!")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print()
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()
    
    # Focus on ISO Week 9 (Feb 23-27)
    week9_dates = [date(2026, 2, 23), date(2026, 2, 24), date(2026, 2, 25), 
                   date(2026, 2, 26), date(2026, 2, 27)]
    
    # Check each team
    teams_pass = True
    
    for team in teams:
        print(f"{team.name} (ID={team.id}) - ISO Week 9 (Feb 23-27):")
        
        # Get team members
        team_members = [e for e in employees if e.team_id == team.id]
        
        # Expected shift for each team based on rotation
        # Team Alpha (id=1, idx=0): (9 + 0) % 3 = 0 → F
        # Team Beta (id=2, idx=1): (9 + 1) % 3 = 1 → N
        # Team Gamma (id=3, idx=2): (9 + 2) % 3 = 2 → S
        team_idx = team.id - 1
        rotation = ["F", "N", "S"]
        expected_shift = rotation[(9 + team_idx) % 3]
        
        print(f"  Expected shift: {expected_shift}")
        print(f"  Checking {len(team_members)} team members:")
        
        team_ok = True
        for emp in team_members:
            # Get employee's shifts for week 9
            emp_week9_shifts = []
            for d in week9_dates:
                for a in assignments:
                    if a.employee_id == emp.id and a.date == d:
                        st = next((s for s in shift_types if s.id == a.shift_type_id), None)
                        if st:
                            emp_week9_shifts.append(st.code)
                        break
            
            # Check if all shifts match expected
            if emp_week9_shifts:
                all_match = all(s == expected_shift for s in emp_week9_shifts)
                status = "✓" if all_match else "✗"
                shifts_str = ", ".join(emp_week9_shifts)
                
                print(f"    {status} {emp.vorname} {emp.name}: {shifts_str}")
                
                if not all_match:
                    team_ok = False
                    teams_pass = False
            else:
                print(f"    - {emp.vorname} {emp.name}: (no shifts)")
        
        print()
        
        if not team_ok:
            print(f"  ❌ {team.name} has members with incorrect shifts!")
        else:
            print(f"  ✅ {team.name} - All members follow team rotation correctly!")
        print()
    
    print("="*80)
    if teams_pass:
        print("✅ SUCCESS: All teams follow their rotation pattern correctly!")
        print("   The cross-team override fix is working as expected.")
        return True
    else:
        print("❌ FAILURE: Some team members have incorrect shifts!")
        print("   The cross-team override bug is still present.")
        return False

if __name__ == "__main__":
    success = test_february_2026_realistic_scenario()
    sys.exit(0 if success else 1)
