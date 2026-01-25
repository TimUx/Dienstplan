#!/usr/bin/env python3
"""
Test script to reproduce the Januar 2026 planning issue.
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning, get_infeasibility_diagnostics
from entities import STANDARD_SHIFT_TYPES

def test_januar_2026():
    """Test planning for Januar 2026 (35 days)"""
    
    # Generate sample data
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    # Define Januar 2026 planning period
    # Januar 2026: Thu Jan 1 - Sat Jan 31 = 35 days
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
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
    
    # Get diagnostics before solving
    print("\n" + "="*60)
    print("RUNNING DIAGNOSTICS")
    print("="*60)
    diagnostics = get_infeasibility_diagnostics(planning_model)
    
    print(f"\nModel Statistics:")
    print(f"  - Total employees: {diagnostics['total_employees']}")
    print(f"  - Employees with absences: {diagnostics['employees_with_absences']}")
    print(f"  - Planning period: {diagnostics['planning_days']} days ({diagnostics['planning_weeks']:.1f} weeks)")
    print(f"  - Absence ratio: {diagnostics['absence_ratio']*100:.1f}%")
    
    if diagnostics['potential_issues']:
        print(f"\n⚠️  Potential Issues Detected ({len(diagnostics['potential_issues'])}):")
        for issue in diagnostics['potential_issues']:
            print(f"  • {issue}")
    else:
        print("\n✓ No obvious issues detected in diagnostics")
        print("  (But the solver may still find the problem infeasible)")
    
    print(f"\nShift Staffing Analysis:")
    for shift_code, analysis in diagnostics['shift_analysis'].items():
        status = "✓" if analysis['is_feasible'] else "✗"
        print(f"  {status} {shift_code}: {analysis['eligible_employees']} eligible / {analysis['min_required']} required")
    
    print(f"\nTeam Configuration:")
    for team_name, info in diagnostics['team_analysis'].items():
        allowed = info['allowed_shifts'] if isinstance(info['allowed_shifts'], str) else f"{len(info['allowed_shifts'])} specific shifts"
        rotation = "Yes" if info['participates_in_rotation'] else "No"
        print(f"  - {team_name}: {info['size']} members, rotation: {rotation}, allowed shifts: {allowed}")
    
    # Try to solve
    print("\n" + "="*60)
    print("ATTEMPTING TO SOLVE")
    print("="*60)
    result = solve_shift_planning(planning_model, time_limit_seconds=60, global_settings=global_settings)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ SUCCESS! Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
        print(f"  - Complete schedule entries: {len(complete_schedule)}")
    else:
        print("\n✗ FAILED! No solution found for Januar 2026")
        print("\nThis reproduces the issue from the problem statement:")
        print("  - Mitarbeiter gesamt: 16")
        print("  - Teams: 3")
        print("  - Planungszeitraum: 35 Tage (5.0 Wochen)")
        print("  - Die genaue Ursache konnte nicht automatisch ermittelt werden")

if __name__ == "__main__":
    test_januar_2026()
