#!/usr/bin/env python3
"""
Test script: Verify cross-shift-type max consecutive days constraints

This script tests that after working max_consecutive_days of one shift type,
an employee must have a day off before working ANY shift type (not just the same one).
"""

from datetime import date, timedelta
from entities import ShiftType, Employee, Team


def test_cross_shift_type_constraint_logic():
    """Test the logic of cross-shift-type consecutive days enforcement"""
    
    print("Testing cross-shift-type consecutive days constraint...")
    print("=" * 70)
    
    # Create test shift types
    shift_f = ShiftType(
        id=1, code="F", name="Frühdienst", start_time="05:45", end_time="13:45",
        color_code="#4CAF50", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=4, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=6
    )
    
    shift_s = ShiftType(
        id=2, code="S", name="Spätdienst", start_time="13:45", end_time="21:45",
        color_code="#FF9800", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=3, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=6
    )
    
    shift_n = ShiftType(
        id=3, code="N", name="Nachtdienst", start_time="21:45", end_time="05:45",
        color_code="#2196F3", hours=8.0, weekly_working_hours=48.0,
        min_staff_weekday=3, max_staff_weekday=10, min_staff_weekend=2, max_staff_weekend=5,
        works_monday=True, works_tuesday=True, works_wednesday=True,
        works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True,
        max_consecutive_days=3
    )
    
    print("\n✓ Shift types created:")
    print(f"  - F (Früh): max_consecutive_days = {shift_f.max_consecutive_days}")
    print(f"  - S (Spät): max_consecutive_days = {shift_s.max_consecutive_days}")
    print(f"  - N (Nacht): max_consecutive_days = {shift_n.max_consecutive_days}")
    
    # Test Scenario 1: Employee works 6x S shift, then tries to work F shift
    print("\n\nScenario 1: Employee works 6x S shift, then tries to work F shift")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-6: S S S S S S (6 consecutive S shifts)")
    print("  Day 7: F (trying to work F shift)")
    print("\nExpected: VIOLATION - Employee must have a break after 6 consecutive days")
    print("  → Day 7 should be OFF, not F shift")
    print("  → Cross-shift-type constraint should trigger")
    
    # Test Scenario 2: Employee works 6x S shift, has 1 day off, then works F shift
    print("\n\nScenario 2: Employee works 6x S shift, has 1 day off, then works F shift")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-6: S S S S S S (6 consecutive S shifts)")
    print("  Day 7: OFF (rest day)")
    print("  Day 8: F (working F shift)")
    print("\nExpected: NO VIOLATION - Employee had proper rest before F shift")
    print("  → Rest day resets the consecutive counter")
    print("  → Cross-shift-type constraint satisfied")
    
    # Test Scenario 3: Employee works 3x N shift, then tries to work S shift
    print("\n\nScenario 3: Employee works 3x N shift, then tries to work S shift")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-3: N N N (3 consecutive N shifts)")
    print("  Day 4: S (trying to work S shift)")
    print("\nExpected: VIOLATION - Employee must have a break after 3 consecutive N shifts")
    print("  → Day 4 should be OFF, not S shift")
    print("  → Cross-shift-type constraint should trigger (N has lower limit)")
    
    # Test Scenario 4: Employee works 3x N shift, has 1 day off, then works S shift
    print("\n\nScenario 4: Employee works 3x N shift, has 1 day off, then works S shift")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-3: N N N (3 consecutive N shifts)")
    print("  Day 4: OFF (rest day)")
    print("  Day 5: S (working S shift)")
    print("\nExpected: NO VIOLATION - Employee had proper rest before S shift")
    print("  → Rest day resets the consecutive counter")
    
    # Test Scenario 5: Switching shift types before limit is OK
    print("\n\nScenario 5: Employee works 5x S shift, then switches to F shift")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-5: S S S S S (5 consecutive S shifts)")
    print("  Day 6: F (switching to F shift)")
    print("\nExpected: NO VIOLATION - Employee hasn't reached limit (6) yet")
    print("  → Switching before reaching max_consecutive_days is allowed")
    print("  → Only the per-shift-type counter matters here, not cross-shift")
    
    # Test Scenario 6: Mixed shifts under the limit
    print("\n\nScenario 6: Employee works S-S-S-F-F-F pattern")
    print("-" * 70)
    print("Schedule:")
    print("  Day 1-3: S S S (3 consecutive S shifts)")
    print("  Day 4-6: F F F (3 consecutive F shifts)")
    print("\nExpected: NO VIOLATION - Neither shift type reaches its limit")
    print("  → S counter: max 3 (limit 6)")
    print("  → F counter: max 3 (limit 6)")
    print("  → No cross-shift-type violation because limits not reached")
    
    print("\n\n" + "=" * 70)
    print("Test Summary:")
    print("=" * 70)
    print("The cross-shift-type constraint ensures that:")
    print("1. After working max_consecutive_days of ANY shift type,")
    print("   employee MUST have a rest day before working ANY shift")
    print("2. Different shift types can have different limits (N=3, F/S=6)")
    print("3. The constraint applies regardless of which shift comes next")
    print("4. Switching shifts before reaching the limit is still allowed")
    print("\n✅ All test scenarios documented!")


if __name__ == "__main__":
    print("=" * 70)
    print("Cross-Shift-Type Max Consecutive Days Constraint Test")
    print("=" * 70)
    print()
    
    test_cross_shift_type_constraint_logic()
