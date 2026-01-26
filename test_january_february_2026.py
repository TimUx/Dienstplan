#!/usr/bin/env python3
"""
Final verification test - mimics the exact scenario from the problem statement.

Tests that:
1. January 2026 planning works
2. February 2026 planning works (the bug we fixed)
3. No INFEASIBLE constraint errors occur
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES


def main():
    print("=" * 80)
    print("VERIFICATION: January and February 2026 Planning")
    print("=" * 80)
    
    employees, teams, _ = generate_sample_data()
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Test 1: January 2026 (baseline - should work)
    print("\n1. Planning January 2026...")
    jan_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES
    )
    jan_model.global_settings = global_settings
    
    jan_result = solve_shift_planning(jan_model, time_limit_seconds=30, 
                                      global_settings=global_settings)
    
    if jan_result:
        print("   ✓ January planning: SUCCESS")
    else:
        print("   ❌ January planning: FAILED (unexpected)")
        return False
    
    # Test 2: February 2026 (the bug we fixed)
    print("\n2. Planning February 2026...")
    feb_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES
    )
    feb_model.global_settings = global_settings
    
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=30, 
                                      global_settings=global_settings)
    
    if feb_result:
        print("   ✓ February planning: SUCCESS")
    else:
        print("   ❌ February planning: FAILED")
        print("   This is the bug we're trying to fix!")
        return False
    
    print("\n" + "=" * 80)
    print("✓ VERIFICATION PASSED")
    print("  - January 2026: ✓")
    print("  - February 2026: ✓")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
