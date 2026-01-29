#!/usr/bin/env python3
"""
Unit test to verify the fix for locked_employee_shift constraint conflict.

This test verifies that when locked_employee_shift constraints are applied,
they properly update locked_team_shift to prevent conflicts with rotation constraints.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import ShiftPlanningModel
from entities import STANDARD_SHIFT_TYPES


def test_locked_employee_shift_updates_locked_team_shift():
    """
    Test that applying locked_employee_shift properly updates locked_team_shift.
    
    This is the core fix for the February 2026 infeasibility issue.
    """
    
    print("=" * 80)
    print("TEST: locked_employee_shift updates locked_team_shift")
    print("=" * 80)
    
    # Setup
    employees, teams, _ = generate_sample_data()
    
    # Create a realistic date range (full month to avoid all weeks being boundary weeks)
    start_date = date(2026, 2, 1)  # Sunday, Feb 1
    end_date = date(2026, 2, 28)    # Saturday, Feb 28
    
    # Find an employee with a team
    emp_with_team = None
    for emp in employees:
        if emp.team_id:
            emp_with_team = emp
            break
    
    if not emp_with_team:
        print("❌ No employee with team found")
        return False
    
    # Create a locked employee shift for a date in a NON-boundary week
    # Week 0 (Jan 26 - Feb 1) spans boundaries
    # Week 1 (Feb 2 - Feb 8) does NOT span boundaries (all dates within Feb 1-28)
    # Use Monday Feb 9 which is in Week 2
    monday_feb_9 = date(2026, 2, 9)
    locked_employee_shift = {
        (emp_with_team.id, monday_feb_9): "F"  # Lock employee to Frühschicht (F)
    }
    
    print(f"\nEmployee: {emp_with_team.name}")
    print(f"Team: {emp_with_team.team_id}")
    print(f"Locked shift: {monday_feb_9} -> F (in a non-boundary week)")
    print(f"\nInitial locked_team_shift: empty")
    
    # Create model with locked employee shift
    model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES,
        locked_employee_shift=locked_employee_shift
    )
    
    # After initialization, locked_team_shift should be updated
    print(f"\nAfter model initialization:")
    print(f"locked_team_shift entries: {len(model.locked_team_shift)}")
    
    # Verify that the team shift was locked
    # Find which week Monday Feb 9 belongs to
    week_idx = None
    for idx, week_dates in enumerate(model.weeks):
        if monday_feb_9 in week_dates:
            week_idx = idx
            break
    
    if week_idx is None:
        print(f"❌ Monday {monday_feb_9} not found in weeks")
        return False
    
    print(f"Monday Feb 9 is in week {week_idx}")
    
    # Check if locked_team_shift was updated
    expected_key = (emp_with_team.team_id, week_idx)
    if expected_key in model.locked_team_shift:
        locked_shift = model.locked_team_shift[expected_key]
        print(f"✓ Team {emp_with_team.team_id}, Week {week_idx} -> {locked_shift}")
        
        if locked_shift == "F":
            print("\n" + "=" * 80)
            print("✓ TEST PASSED - locked_team_shift properly updated!")
            print("=" * 80)
            return True
        else:
            print(f"❌ Expected shift 'F' but got '{locked_shift}'")
            return False
    else:
        print(f"❌ Expected key {expected_key} not found in locked_team_shift")
        print(f"   Available keys: {list(model.locked_team_shift.keys())}")
        print("\n" + "=" * 80)
        print("❌ TEST FAILED - locked_team_shift not updated")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = test_locked_employee_shift_updates_locked_team_shift()
    exit(0 if success else 1)
