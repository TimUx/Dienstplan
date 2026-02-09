#!/usr/bin/env python3
"""
Test script: Verify that weeks start on Sunday and end on Saturday

This script tests that the week calculation logic correctly uses
Sunday as the first day of the week and Saturday as the last day.
"""

from datetime import date, timedelta


def test_week_extension():
    """Test that weeks are extended to Sunday-Saturday boundaries"""
    
    print("Testing week extension logic...")
    print("=" * 70)
    
    # Test 1: Month starting on Thursday (Jan 2026)
    print("\nTest 1: January 2026 (starts Thu Jan 1, ends Sat Jan 31)")
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday
    
    # Extend to Sunday-Saturday
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        days_back = (start_date.weekday() + 1) % 7
        extended_start = start_date - timedelta(days=days_back)
    
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        days_forward = (5 - end_date.weekday()) % 7
        extended_end = end_date + timedelta(days=days_forward)
    
    print(f"  Original: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"  Extended: {extended_start} ({extended_start.strftime('%A')}) to {extended_end} ({extended_end.strftime('%A')})")
    assert extended_start.weekday() == 6, f"Extended start should be Sunday, got {extended_start.strftime('%A')}"
    assert extended_end.weekday() == 5, f"Extended end should be Saturday, got {extended_end.strftime('%A')}"
    print(f"  ✓ Week extends from Sunday {extended_start} to Saturday {extended_end}")
    
    # Test 2: Month starting on Sunday (Feb 2026)
    print("\nTest 2: February 2026 (starts Sun Feb 1, ends Sat Feb 28)")
    start_date = date(2026, 2, 1)  # Sunday
    end_date = date(2026, 2, 28)   # Saturday
    
    # Extend to Sunday-Saturday
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        days_back = (start_date.weekday() + 1) % 7
        extended_start = start_date - timedelta(days=days_back)
    
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        days_forward = (5 - end_date.weekday()) % 7
        extended_end = end_date + timedelta(days=days_forward)
    
    print(f"  Original: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"  Extended: {extended_start} ({extended_start.strftime('%A')}) to {extended_end} ({extended_end.strftime('%A')})")
    assert extended_start == start_date, "Start should not change (already Sunday)"
    assert extended_end == end_date, "End should not change (already Saturday)"
    print(f"  ✓ No extension needed (already Sunday-Saturday)")
    
    # Test 3: Month starting on Monday (March 2026)
    print("\nTest 3: March 2026 (starts Sun Mar 1, ends Tue Mar 31)")
    start_date = date(2026, 3, 1)  # Sunday
    end_date = date(2026, 3, 31)   # Tuesday
    
    # Extend to Sunday-Saturday
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        days_back = (start_date.weekday() + 1) % 7
        extended_start = start_date - timedelta(days=days_back)
    
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        days_forward = (5 - end_date.weekday()) % 7
        extended_end = end_date + timedelta(days=days_forward)
    
    print(f"  Original: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"  Extended: {extended_start} ({extended_start.strftime('%A')}) to {extended_end} ({extended_end.strftime('%A')})")
    assert extended_start == start_date, "Start should not change (already Sunday)"
    assert extended_end.weekday() == 5, f"Extended end should be Saturday, got {extended_end.strftime('%A')}"
    assert extended_end == date(2026, 4, 4), f"Expected April 4, got {extended_end}"
    print(f"  ✓ Week extends to Saturday {extended_end}")
    
    print("\n✅ All week extension tests passed!")


def test_week_generation():
    """Test that weeks are split at Sunday boundaries"""
    
    print("\n\nTesting week generation logic...")
    print("=" * 70)
    
    # Generate 2 weeks: Sun Feb 1 - Sat Feb 14, 2026
    start_date = date(2026, 2, 1)  # Sunday
    end_date = date(2026, 2, 14)   # Saturday
    
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # Generate weeks (split at Sunday)
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 6 and current_week:  # Sunday
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    print(f"\nDate range: {start_date} to {end_date}")
    print(f"Number of weeks: {len(weeks)}")
    
    for i, week in enumerate(weeks):
        print(f"\nWeek {i+1}:")
        for d in week:
            print(f"  {d} ({d.strftime('%A')})")
        
        # Verify week structure
        assert week[0].weekday() == 6, f"Week {i+1} should start on Sunday, got {week[0].strftime('%A')}"
        assert week[-1].weekday() == 5, f"Week {i+1} should end on Saturday, got {week[-1].strftime('%A')}"
        assert len(week) == 7, f"Week {i+1} should have 7 days, got {len(week)}"
    
    assert len(weeks) == 2, f"Should have 2 weeks, got {len(weeks)}"
    print("\n✅ All week generation tests passed!")


def test_week_boundaries_with_incomplete():
    """Test week generation with incomplete weeks"""
    
    print("\n\nTesting incomplete week boundaries...")
    print("=" * 70)
    
    # Start on Wednesday Feb 4, end on Monday Feb 16
    start_date = date(2026, 2, 4)  # Wednesday
    end_date = date(2026, 2, 16)   # Monday
    
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # Generate weeks (split at Sunday)
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 6 and current_week:  # Sunday
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    print(f"\nDate range: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"Number of weeks: {len(weeks)}")
    
    for i, week in enumerate(weeks):
        print(f"\nWeek {i+1} ({len(week)} days):")
        for d in week:
            print(f"  {d} ({d.strftime('%A')})")
    
    # Week 1 should be incomplete: Wed-Sat (4 days)
    assert len(weeks[0]) == 4, f"First week should have 4 days, got {len(weeks[0])}"
    assert weeks[0][0].weekday() == 2, f"First week should start on Wednesday"
    assert weeks[0][-1].weekday() == 5, f"First week should end on Saturday"
    
    # Week 2 should be full: Sun-Sat (7 days)
    assert len(weeks[1]) == 7, f"Second week should have 7 days, got {len(weeks[1])}"
    assert weeks[1][0].weekday() == 6, f"Second week should start on Sunday"
    assert weeks[1][-1].weekday() == 5, f"Second week should end on Saturday"
    
    # Week 3 should be incomplete: Sun-Mon (2 days)
    assert len(weeks[2]) == 2, f"Third week should have 2 days, got {len(weeks[2])}"
    assert weeks[2][0].weekday() == 6, f"Third week should start on Sunday"
    assert weeks[2][-1].weekday() == 0, f"Third week should end on Monday"
    
    print("\n✅ Incomplete week boundary tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Week Start Sunday Verification Test")
    print("=" * 70)
    
    test_week_extension()
    test_week_generation()
    test_week_boundaries_with_incomplete()
    
    print("\n" + "=" * 70)
    print("✅ All tests passed! Weeks now start on Sunday and end on Saturday.")
    print("=" * 70)
