#!/usr/bin/env python3
"""
Test to verify that double shift assignments are prevented.
An employee should only have one shift per day.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES

def test_no_double_shifts():
    """Test that no employee is assigned multiple shifts on the same day"""
    
    print("=" * 70)
    print("TESTING DOUBLE SHIFT PREVENTION")
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
    
    # Plan a week
    start = date(2026, 3, 30)  # Monday
    end = date(2026, 4, 5)     # Sunday
    
    print(f"\nPlanning period: {start} to {end}")
    
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
    
    # Check for double shifts
    print("\n" + "=" * 70)
    print("CHECKING FOR DOUBLE SHIFTS")
    print("=" * 70)
    
    # Group assignments by (employee, date)
    employee_date_assignments = {}
    for assignment in assignments:
        key = (assignment.employee_id, assignment.date)
        if key not in employee_date_assignments:
            employee_date_assignments[key] = []
        employee_date_assignments[key].append(assignment)
    
    # Find double shifts
    double_shifts_found = []
    for (emp_id, d), assigns in employee_date_assignments.items():
        if len(assigns) > 1:
            emp = next((e for e in employees if e.id == emp_id), None)
            emp_name = emp.name if emp else f"Employee {emp_id}"
            
            shift_codes = []
            for a in assigns:
                for st in STANDARD_SHIFT_TYPES:
                    if st.id == a.shift_type_id:
                        shift_codes.append(st.code)
                        break
            
            double_shifts_found.append({
                'employee': emp_name,
                'date': d,
                'shifts': shift_codes,
                'count': len(assigns)
            })
    
    if double_shifts_found:
        print(f"\n❌ FOUND {len(double_shifts_found)} DOUBLE SHIFT VIOLATIONS:")
        for ds in double_shifts_found:
            print(f"  - {ds['employee']} on {ds['date']}: {ds['count']} shifts ({', '.join(ds['shifts'])})")
        
        print("\n" + "=" * 70)
        print("❌ DOUBLE SHIFT TEST FAILED")
        print("=" * 70)
        return False
    else:
        print("\n✓ NO DOUBLE SHIFTS FOUND")
        print(f"  All {len(employee_date_assignments)} employee-day combinations have exactly 1 shift")
        
        print("\n" + "=" * 70)
        print("✓ DOUBLE SHIFT TEST PASSED")
        print("=" * 70)
        return True

if __name__ == "__main__":
    success = test_no_double_shifts()
    exit(0 if success else 1)
