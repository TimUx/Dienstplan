#!/usr/bin/env python3
"""
Test script to see if the problem persists with NO absences.
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning, get_infeasibility_diagnostics
from entities import STANDARD_SHIFT_TYPES

def test_no_absences():
    """Test planning with NO absences to isolate the issue"""
    
    # Generate sample data
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    # Use NO absences
    absences = []
    
    # Use January 2026 dates (original problem)
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Days: {(end_date - start_date).days + 1}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    print(f"Absences: {len(absences)} (NONE)")
    
    # Use default global settings
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Create planning model
    print("\nCreating planning model...")
    planning_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=absences,
        shift_types=STANDARD_SHIFT_TYPES
    )
    
    # Set global settings on the model
    planning_model.global_settings = global_settings
    
    # Get diagnostics
    diagnostics = get_infeasibility_diagnostics(planning_model)
    
    print(f"\n⚠️  Diagnostics ({len(diagnostics['potential_issues'])} issues):")
    for issue in diagnostics['potential_issues']:
        print(f"  • {issue}")
    
    # Try to solve
    print("\n" + "="*60)
    print("ATTEMPTING TO SOLVE (NO ABSENCES)")
    print("="*60)
    result = solve_shift_planning(planning_model, time_limit_seconds=120, global_settings=global_settings)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ SUCCESS! Solution found with NO absences!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
        print(f"  - Complete schedule entries: {len(complete_schedule)}")
        print(f"\nConclusion: The partial weeks are the main issue")
    else:
        print("\n✗ FAILED! Even with NO absences, no solution found")
        print("Conclusion: The partial weeks make it mathematically impossible")

if __name__ == "__main__":
    test_no_absences()
