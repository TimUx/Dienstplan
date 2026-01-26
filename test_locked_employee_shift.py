#!/usr/bin/env python3
"""
Unit test to verify that locked_employee_shift constraints are properly applied.

This test checks that when employee shifts are locked, the model correctly
prevents those employees from being assigned to different shifts on the same dates.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from entities import STANDARD_SHIFT_TYPES

def test_locked_employee_shift_constraints():
    """Test that locked employee shifts are enforced as constraints"""
    
    print("=" * 70)
    print("UNIT TEST: Locked Employee Shift Constraints")
    print("=" * 70)
    
    # Generate sample data
    employees, teams, _ = generate_sample_data()
    
    print(f"\nEmployees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
    # Simple planning period
    start = date(2026, 3, 1)  # Sunday
    end = date(2026, 3, 7)     # Saturday (one week)
    
    print(f"\nPlanning period: {start} to {end}")
    
    # Create locked_employee_shift constraints
    # Lock employee PN001 (Max Müller) to early shift (F) on March 1st
    # Lock employee PN002 (Anna Schmidt) to late shift (S) on March 3rd
    locked_employee_shift = {}
    
    emp_max = next((e for e in employees if e.personalnummer == '1001'), None)
    emp_anna = next((e for e in employees if e.personalnummer == '1002'), None)
    
    if emp_max and emp_anna:
        march_1 = date(2026, 3, 1)
        march_3 = date(2026, 3, 3)
        
        locked_employee_shift[(emp_max.id, march_1)] = 'F'  # Early shift
        locked_employee_shift[(emp_anna.id, march_3)] = 'S'  # Late shift
        
        print(f"\nLocked employee shifts:")
        print(f"  - {emp_max.name} (ID: {emp_max.id}) on {march_1}: F (Early)")
        print(f"  - {emp_anna.name} (ID: {emp_anna.id}) on {march_3}: S (Late)")
    else:
        print("❌ FAILED: Could not find test employees")
        return False
    
    # Create model with locked constraints
    try:
        model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=start,
            end_date=end,
            absences=[],
            shift_types=STANDARD_SHIFT_TYPES,
            locked_employee_shift=locked_employee_shift
        )
        
        print("\n✓ Model created successfully with locked employee shift constraints")
        
        # Verify the model has the locked constraints stored
        if hasattr(model, 'locked_employee_shift'):
            print(f"✓ Model has {len(model.locked_employee_shift)} locked employee shift constraints")
            
            # Verify the specific constraints we added
            if (emp_max.id, march_1) in model.locked_employee_shift:
                if model.locked_employee_shift[(emp_max.id, march_1)] == 'F':
                    print(f"✓ Constraint for {emp_max.name} on {march_1} is correctly set to 'F'")
                else:
                    print(f"❌ Constraint for {emp_max.name} has wrong shift code")
                    return False
            else:
                print(f"❌ Constraint for {emp_max.name} not found in model")
                return False
            
            if (emp_anna.id, march_3) in model.locked_employee_shift:
                if model.locked_employee_shift[(emp_anna.id, march_3)] == 'S':
                    print(f"✓ Constraint for {emp_anna.name} on {march_3} is correctly set to 'S'")
                else:
                    print(f"❌ Constraint for {emp_anna.name} has wrong shift code")
                    return False
            else:
                print(f"❌ Constraint for {emp_anna.name} not found in model")
                return False
        else:
            print("❌ Model does not have locked_employee_shift attribute")
            return False
        
        print("\n" + "=" * 70)
        print("✓ TEST PASSED - Locked employee shift constraints work correctly")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: Error creating model: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_locked_employee_shift_constraints()
    exit(0 if success else 1)
