#!/usr/bin/env python3
"""
Test January 2026 planning WITH week extension (until Sunday Feb 1).
This extends the partial last week to make complete weeks for planning.
"""

import sys
from datetime import date, timedelta
from data_loader import init_db, add_test_data, load_planning_data, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import GlobalSettings

def extend_to_complete_weeks(start_date, end_date):
    """Extend end date to next Sunday if not already Sunday."""
    # Calculate days until next Sunday
    days_until_sunday = (6 - end_date.weekday()) % 7
    if days_until_sunday > 0:
        extended_end = end_date + timedelta(days=days_until_sunday)
        return extended_end
    return end_date

def test_january_extended():
    print("=" * 80)
    print("Testing JANUARY 2026 WITH WEEK EXTENSION:")
    
    # Original January period
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday
    
    # Extend to complete weeks
    extended_end = extend_to_complete_weeks(start_date, end_date)
    
    print(f"  Original period: {start_date} to {end_date}")
    print(f"  Extended period: {start_date} to {extended_end}")
    print(f"  Days: {(end_date - start_date).days + 1} → {(extended_end - start_date).days + 1}")
    
    # Calculate weeks
    total_days = (extended_end - start_date).days + 1
    weeks = total_days / 7.0
    print(f"  Weeks: {weeks:.1f} (should be complete weeks now)")
    print("=" * 80)
    print()
    
    # Initialize database with test data
    print("Initializing database...")
    init_db()
    
    print("Adding test data...")
    add_test_data()
    print("✓ Test data created: 3 teams with 5 employees each")
    print()
    
    # Load planning data with EXTENDED dates
    employees, teams, shift_types, absences = load_planning_data(start_date, extended_end)
    print(f"Loaded: {len(employees)} employees, {len(teams)} teams, {len(shift_types)} shift types")
    print()
    
    # Load global settings
    global_settings = load_global_settings()
    
    # Create model with EXTENDED dates
    planning_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        shift_types=shift_types,
        absences=absences,
        start_date=start_date,
        end_date=extended_end,  # USE EXTENDED END DATE
        locked_team_assignments=None
    )
    
    print("Model statistics:")
    planning_model.print_statistics()
    print()
    
    print("Attempting to solve...")
    result = solve_shift_planning(planning_model, time_limit_seconds=180, global_settings=global_settings)
    
    print()
    print("=" * 80)
    if result.get('status') == 'OPTIMAL' or result.get('status') == 'FEASIBLE':
        print(f"✓ {result.get('status')} for January 2026 WITH WEEK EXTENSION!")
        print()
        
        # Show team assignments
        print("Team assignments by week:")
        team_assignments = result.get('team_assignments', {})
        for week_idx in sorted(set(k[1] for k in team_assignments.keys())):
            week_start = start_date + timedelta(weeks=week_idx)
            print(f"  Week {week_idx} (starting {week_start}):")
            for team_id in sorted(set(k[0] for k in team_assignments.keys())):
                shift = team_assignments.get((team_id, week_idx))
                team_name = next((t.name for t in teams if t.id == team_id), f"Team {team_id}")
                print(f"    {team_name}: {shift}")
        
        # Show employee hours
        print()
        print("Employee working hours:")
        employee_assignments = result.get('employee_assignments', {})
        for emp in sorted(employees, key=lambda e: e.id):
            if not emp.team_id:
                continue
            days_worked = sum(1 for (eid, d) in employee_assignments.keys() 
                             if eid == emp.id and employee_assignments[(eid, d)])
            hours = days_worked * 8
            print(f"    {emp.name}: {days_worked} days = {hours}h")
        
        return True
    else:
        print(f"✗ {result.get('status')} for January 2026 WITH WEEK EXTENSION")
        return False
    print("=" * 80)

if __name__ == "__main__":
    success = test_january_extended()
    sys.exit(0 if success else 1)
