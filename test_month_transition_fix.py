#!/usr/bin/env python3
"""
Simple test to verify that month transitions work correctly.
Tests that a week spanning two months gets the same TEAM shift assignment.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES

def test_month_transition():
    """Test that rotation continues across months"""
    
    print("=" * 70)
    print("TESTING MONTH TRANSITION FIX")
    print("=" * 70)
    
    # Generate sample data
    employees, teams, _ = generate_sample_data()
    
    # Use default global settings
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    print(f"\nTeams: {len(teams)}")
    for team in teams:
        members = [e for e in employees if e.team_id == team.id]
        print(f"  - {team.name}: {len(members)} members")
    
    # Test case: Week that spans March-April 2026
    # According to our earlier check:
    # Week 14: March 30 (Mon) to April 5 (Sun)
    # This week spans two months
    
    print("\n" + "=" * 70)
    print("SCENARIO: Week spanning March 30 - April 5, 2026")
    print("=" * 70)
    
    # Plan a short period that includes this week
    # March 30 is already a Monday, so let's plan March 30 - April 5
    start = date(2026, 3, 30)  # Monday
    end = date(2026, 4, 5)     # Sunday
    
    print(f"\nPlanning period: {start} to {end}")
    print(f"ISO week number: {start.isocalendar()[1]}")
    
    # Create model and solve
    model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=start,
        end_date=end,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES
    )
    model.global_settings = global_settings
    
    result = solve_shift_planning(model, time_limit_seconds=60, global_settings=global_settings)
    
    if not result:
        print("❌ FAILED to plan!")
        return False
    
    assignments, special_functions, _ = result
    print(f"✓ Planning successful: {len(assignments)} assignments")
    
    # Analyze TEAM shifts (not cross-team) for this week
    print("\n" + "=" * 70)
    print("TEAM SHIFTS FOR WEEK 14 (March 30 - April 5)")
    print("(Excluding cross-team assignments)")
    print("=" * 70)
    
    # Group assignments by team, excluding cross-team assignments
    team_assignments = {}
    for team in teams:
        team_members = [e.id for e in employees if e.team_id == team.id]
        team_shifts_in_week = set()
        
        for assignment in assignments:
            # Skip cross-team assignments
            if hasattr(assignment, 'notes') and assignment.notes and 'Cross-team' in assignment.notes:
                continue
                
            if assignment.employee_id in team_members:
                if assignment.date >= start and assignment.date <= end:
                    # Find shift code
                    for st in STANDARD_SHIFT_TYPES:
                        if st.id == assignment.shift_type_id:
                            team_shifts_in_week.add(st.code)
                            break
        
        team_assignments[team.name] = team_shifts_in_week
    
    success = True
    for team_name, shifts in sorted(team_assignments.items()):
        print(f"{team_name}: {', '.join(sorted(shifts)) if shifts else 'NO TEAM SHIFTS'}")
        
        # Verify each team has exactly one shift type for the week
        if len(shifts) != 1:
            print(f"  ❌ ERROR: Team has {len(shifts)} different shifts in one week!")
            print(f"  Expected: 1 shift type for entire week")
            success = False
        elif len(shifts) == 1:
            print(f"  ✓ OK: Team has consistent shift throughout the week")
    
    if success:
        print("\n" + "=" * 70)
        print("✓ MONTH TRANSITION TEST PASSED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ MONTH TRANSITION TEST FAILED")
        print("=" * 70)
        
    return success

if __name__ == "__main__":
    success = test_month_transition()
    exit(0 if success else 1)
