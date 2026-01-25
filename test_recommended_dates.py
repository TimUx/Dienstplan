#!/usr/bin/env python3
"""
Test script to verify that the recommended dates work.
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES

def test_recommended_dates():
    """Test planning with the recommended dates (Mon Dec 29, 2025 to Sun Feb 1, 2026)"""
    
    # Generate sample data
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    # Use recommended dates from diagnostics
    # Start: Monday, December 29, 2025
    # End: Sunday, February 1, 2026
    start_date = date(2025, 12, 29)
    end_date = date(2026, 2, 1)
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Days: {(end_date - start_date).days + 1}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
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
    
    # Print model statistics
    planning_model.print_model_statistics()
    
    # Try to solve
    print("\n" + "="*60)
    print("ATTEMPTING TO SOLVE WITH RECOMMENDED DATES")
    print("="*60)
    result = solve_shift_planning(planning_model, time_limit_seconds=60, global_settings=global_settings)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ SUCCESS! Solution found with recommended dates!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
        print(f"  - Complete schedule entries: {len(complete_schedule)}")
        print(f"\nThis confirms that the diagnostics correctly identified the issue")
        print(f"and the recommended date range (Mon-Sun full weeks) works!")
    else:
        print("\n✗ FAILED! Even with recommended dates, no solution found")
        print("This suggests there may be other underlying issues")

if __name__ == "__main__":
    test_recommended_dates()
