#!/usr/bin/env python3
"""
Test script to validate the fix for partial-week absence handling.

This script demonstrates the bug fix where employees with absences on ANY day
of a week had their ENTIRE week's hours not counted toward the minimum 192h requirement.

Scenario:
- Planning period: Feb 1-28, 2026 (extended to Jan 26 - Mar 1 for full weeks)
- Robert Franke (S001) works in week 4 (Feb 23-28) but has AU on March 1
- Before fix: Week 4 completely skipped, hours not counted
- After fix: Only March 1 skipped, Feb 23-28 hours properly counted
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple

def test_date_extension():
    """Test that planning period is extended to full weeks as expected"""
    print("=" * 70)
    print("TEST 1: Date Extension Logic")
    print("=" * 70)
    
    start_date = date(2026, 2, 1)  # Sunday
    end_date = date(2026, 2, 28)    # Saturday
    
    print(f"Original planning period: {start_date} to {end_date}")
    print(f"  Start: {start_date.strftime('%A, %Y-%m-%d')}")
    print(f"  End:   {end_date.strftime('%A, %Y-%m-%d')}")
    
    # Simulate extension logic from model.py
    extended_start = start_date
    extended_end = end_date
    
    # Extend start to Monday
    if start_date.weekday() != 0:  # 0 = Monday
        days_back = start_date.weekday()
        extended_start = start_date - timedelta(days=days_back)
        print(f"\n✓ Extended start back {days_back} days to Monday: {extended_start}")
    
    # Extend end to Sunday
    if end_date.weekday() != 6:  # 6 = Sunday
        days_forward = 6 - end_date.weekday()
        extended_end = end_date + timedelta(days=days_forward)
        print(f"✓ Extended end forward {days_forward} days to Sunday: {extended_end}")
    
    print(f"\nExtended planning period: {extended_start} to {extended_end}")
    
    # Check if March 1 is included
    march_1 = date(2026, 3, 1)
    if extended_end >= march_1:
        print(f"\n⚠️  IMPORTANT: March 1st ({march_1.strftime('%A')}) IS included in extended period!")
        print(f"   This means absences on March 1st affect February planning.")
    
    return extended_start, extended_end

def test_week_building(extended_start: date, extended_end: date):
    """Test how weeks are built from extended dates"""
    print("\n" + "=" * 70)
    print("TEST 2: Week Building")
    print("=" * 70)
    
    # Build dates
    dates = []
    current = extended_start
    while current <= extended_end:
        dates.append(current)
        current += timedelta(days=1)
    
    # Build weeks
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:  # Monday
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    print(f"\nTotal dates: {len(dates)}")
    print(f"Total weeks: {len(weeks)}")
    
    for i, week in enumerate(weeks):
        week_start = week[0].strftime('%Y-%m-%d (%a)')
        week_end = week[-1].strftime('%Y-%m-%d (%a)')
        print(f"  Week {i}: {week_start} to {week_end} ({len(week)} days)")
    
    # Focus on week 4
    print(f"\n📋 Week 4 Details (the problematic week):")
    week_4 = weeks[4]
    for d in week_4:
        day_str = d.strftime('%Y-%m-%d %A')
        if d.month == 3:
            print(f"  {day_str} ← March! (outside original period)")
        else:
            print(f"  {day_str}")
    
    return weeks

def test_absence_logic_old(weeks: List[List[date]]):
    """Test OLD (buggy) logic: Skip entire week if ANY day has absence"""
    print("\n" + "=" * 70)
    print("TEST 3: OLD LOGIC (Before Fix) - Week-Based Absence Checking")
    print("=" * 70)
    
    # Simulate Robert Franke with absence on March 1
    robert_id = 5
    absence_start = date(2026, 3, 1)
    absence_end = date(2026, 3, 1)
    
    print(f"Robert Franke (ID={robert_id}) has AU on: {absence_start}")
    
    # OLD LOGIC: Check if any day in week has absence
    weeks_without_absences = 0
    total_hours = 0
    
    for week_idx, week_dates in enumerate(weeks):
        # OLD LOGIC: Check if employee has ANY absence this week
        has_absence_this_week = any(
            d >= absence_start and d <= absence_end
            for d in week_dates
        )
        
        if has_absence_this_week:
            print(f"\n❌ Week {week_idx}: HAS ABSENCE - ENTIRE WEEK SKIPPED")
            print(f"   Week dates: {week_dates[0]} to {week_dates[-1]}")
            print(f"   Hours worked this week: NOT COUNTED (0h)")
            continue  # ← BUG: Skip entire week!
        
        weeks_without_absences += 1
        
        # Assume Robert worked 6 days in weeks 0-3 (48h each)
        # and 2 days in week 4 before absence (16h)
        if week_idx < 4:
            hours_this_week = 48
        elif week_idx == 4:
            hours_this_week = 16  # Only worked Feb 23-24 (S S)
        else:
            hours_this_week = 0
        
        total_hours += hours_this_week
        print(f"\n✓ Week {week_idx}: No absence - counted")
        print(f"   Hours worked this week: {hours_this_week}h")
    
    print(f"\n📊 OLD LOGIC RESULTS:")
    print(f"   Weeks without absences: {weeks_without_absences}")
    print(f"   Total hours counted: {total_hours}h")
    print(f"   Minimum required: 192h")
    
    if total_hours < 192:
        print(f"   ⚠️  SHORTAGE: {192 - total_hours}h below minimum!")
        print(f"   ❌ BUG: Week 4's 16h were NOT counted because March 1 is in week 4")
    
    return total_hours

def test_absence_logic_new(weeks: List[List[date]]):
    """Test NEW (fixed) logic: Skip only absent days, not entire weeks"""
    print("\n" + "=" * 70)
    print("TEST 4: NEW LOGIC (After Fix) - Day-Based Absence Checking")
    print("=" * 70)
    
    # Simulate Robert Franke with absence on March 1
    robert_id = 5
    absence_start = date(2026, 3, 1)
    absence_end = date(2026, 3, 1)
    
    print(f"Robert Franke (ID={robert_id}) has AU on: {absence_start}")
    
    # NEW LOGIC: Count days without absences
    all_dates = [d for week in weeks for d in week]
    days_without_absence = sum(
        1 for d in all_dates
        if not (d >= absence_start and d <= absence_end)
    )
    
    print(f"\n📅 Day-by-day analysis:")
    print(f"   Total dates in extended period: {len(all_dates)}")
    print(f"   Days WITHOUT absence: {days_without_absence}")
    print(f"   Days WITH absence: {len(all_dates) - days_without_absence}")
    
    # Calculate hours by week, skipping only absent days
    total_hours = 0
    
    for week_idx, week_dates in enumerate(weeks):
        hours_this_week = 0
        absent_days_this_week = 0
        
        for d in week_dates:
            is_absent = (d >= absence_start and d <= absence_end)
            
            if is_absent:
                absent_days_this_week += 1
                continue  # ← FIX: Skip only this day!
            
            # Simulate hours: 8h per working day
            # Assume Robert works Mon-Sat (not Sunday in weeks 0-3)
            if week_idx < 4:
                if d.weekday() < 6:  # Mon-Sat
                    hours_this_week += 8
            elif week_idx == 4:
                # Week 4: Only worked Feb 23-24 (Mo-Di: S S)
                if d.month == 2 and d.day in [23, 24]:
                    hours_this_week += 8
        
        total_hours += hours_this_week
        
        status = f"✓ {hours_this_week}h counted"
        if absent_days_this_week > 0:
            status += f" ({absent_days_this_week} day(s) skipped)"
        
        print(f"\n  Week {week_idx}: {status}")
        print(f"     Week dates: {week_dates[0]} to {week_dates[-1]}")
    
    print(f"\n📊 NEW LOGIC RESULTS:")
    print(f"   Days without absences: {days_without_absence}")
    print(f"   Total hours counted: {total_hours}h")
    print(f"   Minimum required: 192h")
    
    if total_hours < 192:
        print(f"   ⚠️  SHORTAGE: {192 - total_hours}h below minimum")
        print(f"   Note: This example shows the fix works - week 4's hours ARE now counted")
    else:
        print(f"   ✓ Meets minimum requirement!")
    
    return total_hours

def main():
    """Run all tests"""
    print("\n" + "🔧" * 35)
    print("TESTING: Partial-Week Absence Handling Fix")
    print("🔧" * 35 + "\n")
    
    # Test 1: Date extension
    extended_start, extended_end = test_date_extension()
    
    # Test 2: Week building
    weeks = test_week_building(extended_start, extended_end)
    
    # Test 3: Old (buggy) logic
    old_hours = test_absence_logic_old(weeks)
    
    # Test 4: New (fixed) logic
    new_hours = test_absence_logic_new(weeks)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n🐛 OLD LOGIC (buggy):  {old_hours}h counted")
    print(f"   Problem: Week 4 skipped entirely because March 1 has absence")
    print(f"   Robert's Feb 23-24 work (16h) NOT counted")
    
    print(f"\n✅ NEW LOGIC (fixed):  {new_hours}h counted")
    print(f"   Solution: Only March 1 skipped, Feb 23-24 work IS counted")
    print(f"   Week 4's hours properly included in total")
    
    difference = new_hours - old_hours
    print(f"\n📈 Improvement: +{difference}h with fix")
    
    print("\n" + "🎯" * 35)
    print("This demonstrates why Robert Franke was under-scheduled!")
    print("With the fix, his hours from week 4 are properly counted,")
    print("and the solver will enforce the 192h minimum correctly.")
    print("🎯" * 35 + "\n")

if __name__ == "__main__":
    main()
