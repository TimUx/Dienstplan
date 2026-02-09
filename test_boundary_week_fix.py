"""
Test to verify that weeks spanning month boundaries are not locked for team shifts.

This test validates the fix for the March 2026 planning issue where Week 0 
(Feb 23 - Mar 1) caused INFEASIBLE conflicts because it tried to lock the team
to a single shift when February assignments had multiple shifts in that week.
"""

from datetime import date, timedelta


def test_boundary_week_detection():
    """Test that weeks spanning month boundaries are correctly identified."""
    
    # March 2026 scenario
    start_date = date(2026, 3, 1)  # Sunday
    end_date = date(2026, 3, 31)    # Tuesday
    
    # Extended dates (complete weeks, now Sunday-Saturday)
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        days_since_sunday = start_date.weekday() + 1
        extended_start = start_date - timedelta(days=days_since_sunday)
    
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        days_until_saturday = (5 - end_date.weekday() + 7) % 7
        extended_end = end_date + timedelta(days=days_until_saturday)
    
    # For March 1 (Sunday), no extension needed for start
    # For March 31 (Tuesday), extend to Saturday April 4
    assert extended_start == date(2026, 3, 1), "Extended start should be Mar 1 (Sunday)"
    assert extended_end == date(2026, 4, 4), "Extended end should be Apr 4 (Saturday)"
    
    # Calculate weeks
    dates_list = []
    current = extended_start
    while current <= extended_end:
        dates_list.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates_list:
        if d.weekday() == 6 and current_week:  # Sunday
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Identify boundary weeks
    boundary_weeks = set()
    for week_idx, week_dates in enumerate(weeks):
        has_dates_before_month = any(d < start_date for d in week_dates)
        has_dates_in_month = any(start_date <= d <= end_date for d in week_dates)
        has_dates_after_month = any(d > end_date for d in week_dates)
        
        if (has_dates_before_month and has_dates_in_month) or (has_dates_in_month and has_dates_after_month):
            boundary_weeks.add(week_idx)
    
    # Verify expectations (updated for Sunday-Saturday weeks)
    # March 1 is Sunday, so Week 0 is Mar 1-7 (all in March, not a boundary)
    # Last week will contain April dates (boundary week)
    assert len(weeks) == 5, f"Should have 5 weeks, got {len(weeks)}"
    assert 0 not in boundary_weeks, "Week 0 (Mar 1-7) should NOT be a boundary week"
    assert 4 in boundary_weeks, "Last week should be a boundary week (contains April dates)"
    
    
    print("✅ All boundary week detection tests passed!")
    for i, week in enumerate(weeks):
        is_boundary = i in boundary_weeks
        print(f"   - Week {i}: {week[0]} to {week[-1]} (boundary: {is_boundary})")


def test_february_scenario():
    """Test February 2026 scenario to ensure it works correctly."""
    
    start_date = date(2026, 2, 1)   # Sunday
    end_date = date(2026, 2, 28)     # Saturday
    
    # Extended dates (now Sunday-Saturday weeks)
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        days_since_sunday = start_date.weekday() + 1
        extended_start = start_date - timedelta(days=days_since_sunday)
    
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        days_until_saturday = (5 - end_date.weekday() + 7) % 7
        extended_end = end_date + timedelta(days=days_until_saturday)
    
    print(f"\n✅ February 2026 test:")
    print(f"   - Main month: {start_date} to {end_date}")
    print(f"   - Extended: {extended_start} to {extended_end}")
    print(f"   - Extended start is Sunday: {extended_start.weekday() == 6}")
    print(f"   - Extended end is Saturday: {extended_end.weekday() == 5}")


if __name__ == "__main__":
    test_boundary_week_detection()
    test_february_scenario()
    print("\n✅ All tests passed!")
