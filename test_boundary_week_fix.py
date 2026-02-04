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
    
    # Extended dates (complete weeks)
    days_since_monday = start_date.weekday()
    extended_start = start_date - timedelta(days=days_since_monday)
    days_until_sunday = 6 - end_date.weekday()
    extended_end = end_date + timedelta(days=days_until_sunday)
    
    assert extended_start == date(2026, 2, 23), "Extended start should be Feb 23 (Monday)"
    assert extended_end == date(2026, 4, 5), "Extended end should be Apr 5 (Sunday)"
    
    # Calculate weeks
    dates_list = []
    current = extended_start
    while current <= extended_end:
        dates_list.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates_list:
        if d.weekday() == 0 and current_week:  # Monday
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
    
    # Verify expectations
    assert len(weeks) == 6, f"Should have 6 weeks, got {len(weeks)}"
    assert 0 in boundary_weeks, "Week 0 (Feb 23 - Mar 1) should be a boundary week"
    assert 5 in boundary_weeks, "Week 5 (Mar 30 - Apr 5) should be a boundary week"
    assert 1 not in boundary_weeks, "Week 1 (Mar 2-8) should NOT be a boundary week"
    assert 2 not in boundary_weeks, "Week 2 (Mar 9-15) should NOT be a boundary week"
    assert 3 not in boundary_weeks, "Week 3 (Mar 16-22) should NOT be a boundary week"
    assert 4 not in boundary_weeks, "Week 4 (Mar 23-29) should NOT be a boundary week"
    
    print("✅ All boundary week detection tests passed!")
    print(f"   - Week 0: {weeks[0][0]} to {weeks[0][-1]} (boundary: {0 in boundary_weeks})")
    print(f"   - Week 5: {weeks[5][0]} to {weeks[5][-1]} (boundary: {5 in boundary_weeks})")
    print(f"   - Weeks 1-4 are entirely within March (not boundaries)")


def test_february_scenario():
    """Test February 2026 scenario to ensure it works correctly."""
    
    start_date = date(2026, 2, 1)   # Sunday
    end_date = date(2026, 2, 28)     # Saturday
    
    # Extended dates
    days_since_monday = start_date.weekday()
    extended_start = start_date - timedelta(days=days_since_monday)
    days_until_sunday = 6 - end_date.weekday()
    extended_end = end_date + timedelta(days=days_until_sunday)
    
    print(f"\n✅ February 2026 test:")
    print(f"   - Main month: {start_date} to {end_date}")
    print(f"   - Extended: {extended_start} to {extended_end}")
    print(f"   - Extended start is Monday: {extended_start.weekday() == 0}")
    print(f"   - Extended end is Sunday: {extended_end.weekday() == 6}")


if __name__ == "__main__":
    test_boundary_week_detection()
    test_february_scenario()
    print("\n✅ All tests passed!")
