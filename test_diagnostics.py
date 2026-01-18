"""
Test the new diagnostic features for infeasibility detection.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning, get_infeasibility_diagnostics
from entities import Absence, AbsenceType


def test_diagnostics_with_infeasible_scenario():
    """
    Test that diagnostics provide helpful information when planning fails.
    
    Create a scenario that's likely to be infeasible by having many absences.
    """
    print("\n" + "=" * 70)
    print("TEST: Diagnostic Information for Infeasible Scenario")
    print("=" * 70)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Define planning period
    start_date = date.today()
    end_date = start_date + timedelta(days=13)  # 2 weeks
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
    # Add many absences to make it harder to solve
    # This simulates a scenario where many employees are absent
    additional_absences = [
        Absence(100, 1, AbsenceType.U, start_date, start_date + timedelta(days=7), "Vacation"),
        Absence(101, 2, AbsenceType.U, start_date + timedelta(days=3), start_date + timedelta(days=10), "Vacation"),
        Absence(102, 6, AbsenceType.AU, start_date, start_date + timedelta(days=5), "Sick"),
        Absence(103, 7, AbsenceType.AU, start_date + timedelta(days=6), start_date + timedelta(days=12), "Sick"),
        Absence(104, 11, AbsenceType.L, start_date, start_date + timedelta(days=4), "Training"),
    ]
    
    all_absences = absences + additional_absences
    
    print(f"\nTotal absences: {len(all_absences)}")
    
    # Create model
    print("\nCreating shift planning model...")
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, all_absences
    )
    
    # Get diagnostics before solving
    print("\n--- PRE-SOLVE DIAGNOSTICS ---")
    diagnostics = get_infeasibility_diagnostics(planning_model)
    
    print(f"\nModel Statistics:")
    print(f"  Total employees: {diagnostics['total_employees']}")
    print(f"  Available employees: {diagnostics['available_employees']}")
    print(f"  Absent employees: {diagnostics['absent_employees']}")
    print(f"  Planning days: {diagnostics['planning_days']}")
    
    if diagnostics['potential_issues']:
        print(f"\n⚠️  Potential Issues Detected ({len(diagnostics['potential_issues'])}):")
        for issue in diagnostics['potential_issues']:
            print(f"  • {issue}")
    
    print(f"\nShift Staffing Analysis:")
    for shift_code, analysis in diagnostics['shift_analysis'].items():
        status = "✓" if analysis['is_feasible'] else "✗"
        print(f"  {status} {shift_code}: {analysis['eligible_employees']} eligible / {analysis['min_required']} required")
    
    # Try to solve
    print("\n--- ATTEMPTING TO SOLVE ---")
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✅ SUCCESS: Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
    else:
        print(f"\n❌ NO SOLUTION: As expected, the scenario is infeasible")
        print(f"   The diagnostic information above should help identify why.")
    
    print("\n" + "=" * 70)
    return True


def test_diagnostics_with_feasible_scenario():
    """
    Test that diagnostics work correctly with a feasible scenario.
    """
    print("\n" + "=" * 70)
    print("TEST: Diagnostic Information for Feasible Scenario")
    print("=" * 70)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Define shorter planning period to make it easier to solve
    start_date = date.today()
    end_date = start_date + timedelta(days=6)  # 1 week
    
    print(f"\nPlanning period: {start_date} to {end_date} (1 week)")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
    # Create model
    print("\nCreating shift planning model...")
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences
    )
    
    # Get diagnostics
    print("\n--- PRE-SOLVE DIAGNOSTICS ---")
    diagnostics = get_infeasibility_diagnostics(planning_model)
    
    print(f"\nModel Statistics:")
    print(f"  Total employees: {diagnostics['total_employees']}")
    print(f"  Available employees: {diagnostics['available_employees']}")
    print(f"  Absent employees: {diagnostics['absent_employees']}")
    
    if diagnostics['potential_issues']:
        print(f"\n⚠️  Potential Issues Detected:")
        for issue in diagnostics['potential_issues']:
            print(f"  • {issue}")
    else:
        print(f"\n✓ No obvious issues detected")
    
    # Try to solve
    print("\n--- ATTEMPTING TO SOLVE ---")
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✅ SUCCESS: Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
    else:
        print(f"\n❌ NO SOLUTION: Unexpected - scenario should be feasible")
    
    print("\n" + "=" * 70)
    return result is not None


if __name__ == "__main__":
    print("\nTesting Diagnostic Features")
    print("=" * 70)
    
    # Test with infeasible scenario
    test_diagnostics_with_infeasible_scenario()
    
    # Test with feasible scenario
    test_diagnostics_with_feasible_scenario()
    
    print("\n✓ All diagnostic tests completed!")
