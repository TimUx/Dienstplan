#!/usr/bin/env python3
"""
Test script to verify cross-month planning continuity.

This test validates that:
1. Planning January 2026 extends into early February
2. Planning February 2026 locks the days planned by January
3. The team rotation rhythm continues across months
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import STANDARD_SHIFT_TYPES

def get_team_rotation_for_week(assignments, week_dates, teams):
    """Get which team has which shift for a given week"""
    # Group assignments by team and shift type
    from collections import defaultdict
    team_shifts = defaultdict(set)
    
    for assignment in assignments:
        if assignment.date in week_dates:
            # Find team for this employee
            for team in teams:
                if any(e.id == assignment.employee_id for e in [emp for emp in generate_sample_data()[0] if emp.team_id == team.id]):
                    # Get shift code from shift type ID
                    shift_code = None
                    for st in STANDARD_SHIFT_TYPES:
                        if st.id == assignment.shift_type_id:
                            shift_code = st.code
                            break
                    if shift_code in ['F', 'N', 'S']:
                        team_shifts[team.id].add(shift_code)
    
    return team_shifts

def test_cross_month_continuity():
    """Test that rotation continues across months"""
    
    print("=" * 70)
    print("TESTING CROSS-MONTH PLANNING CONTINUITY")
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
    
    # ========================================================================
    # STEP 1: Plan January 2026 (Thu Jan 1 - Sat Jan 31)
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: Planning January 2026")
    print("=" * 70)
    
    jan_start = date(2026, 1, 1)  # Thursday
    jan_end = date(2026, 1, 31)    # Saturday
    
    # Extend to complete weeks
    jan_extended_start = jan_start - timedelta(days=jan_start.weekday())  # Previous Monday
    jan_extended_end = jan_end + timedelta(days=(6 - jan_end.weekday()))  # Next Sunday
    
    print(f"Requested period: {jan_start} (Thu) to {jan_end} (Sat)")
    print(f"Extended period:  {jan_extended_start} (Mon) to {jan_extended_end} (Sun)")
    print(f"Days extending into February: {(jan_extended_end - jan_end).days}")
    
    # Create model and solve
    jan_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=jan_extended_start,
        end_date=jan_extended_end,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES
    )
    jan_model.global_settings = global_settings
    
    jan_result = solve_shift_planning(jan_model, time_limit_seconds=120, global_settings=global_settings)
    
    if not jan_result:
        print("❌ FAILED to plan January 2026!")
        return
    
    jan_assignments, jan_special_functions, _ = jan_result
    print(f"✓ January planned successfully: {len(jan_assignments)} assignments")
    
    # Identify assignments that extend into February
    feb_days_from_jan = [a for a in jan_assignments if a.date > jan_end]
    print(f"  - Assignments in February from January planning: {len(feb_days_from_jan)}")
    
    # Show team rotation for the last week of January (which extends into February)
    last_week_start = jan_extended_end - timedelta(days=6)  # Monday of last week
    last_week_dates = [last_week_start + timedelta(days=i) for i in range(7)]
    print(f"\n  Last week of January planning: {last_week_dates[0]} to {last_week_dates[-1]}")
    
    # ========================================================================
    # STEP 2: Plan February 2026 (Sun Feb 1 - Sat Feb 28)
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: Planning February 2026")
    print("=" * 70)
    
    feb_start = date(2026, 2, 1)   # Sunday
    feb_end = date(2026, 2, 28)     # Saturday
    
    # Extend to complete weeks
    feb_extended_start = feb_start - timedelta(days=feb_start.weekday()) if feb_start.weekday() != 0 else feb_start
    feb_extended_end = feb_end + timedelta(days=(6 - feb_end.weekday())) if feb_end.weekday() != 6 else feb_end
    
    print(f"Requested period: {feb_start} (Sun) to {feb_end} (Sat)")
    print(f"Extended period:  {feb_extended_start} (Mon) to {feb_extended_end} (Sun)")
    
    # Build locked constraints from January's assignments
    # This simulates what the web API does when loading existing assignments
    locked_team_shift = {}
    
    # Calculate weeks for February extended period
    dates_list = []
    current = feb_extended_start
    while current <= feb_extended_end:
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
    
    # Map dates to week indices
    date_to_week = {}
    for week_idx, week_dates in enumerate(weeks):
        for d in week_dates:
            date_to_week[d] = week_idx
    
    # Lock assignments from January that fall in February's extended period
    for assignment in feb_days_from_jan:
        if assignment.date in date_to_week:
            week_idx = date_to_week[assignment.date]
            # Find which team this employee belongs to
            for emp in employees:
                if emp.id == assignment.employee_id:
                    team_id = emp.team_id
                    # Get shift code
                    for st in STANDARD_SHIFT_TYPES:
                        if st.id == assignment.shift_type_id:
                            shift_code = st.code
                            if shift_code in ['F', 'N', 'S'] and team_id:
                                if (team_id, week_idx) not in locked_team_shift:
                                    locked_team_shift[(team_id, week_idx)] = shift_code
                                    print(f"  Locked: Team {team_id}, Week {week_idx} -> {shift_code} (from Jan planning on {assignment.date})")
                            break
                    break
    
    print(f"\n  Total locked constraints: {len(locked_team_shift)}")
    
    # Create model with locked constraints and solve
    feb_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=feb_extended_start,
        end_date=feb_extended_end,
        absences=[],
        shift_types=STANDARD_SHIFT_TYPES,
        locked_team_shift=locked_team_shift if locked_team_shift else None
    )
    feb_model.global_settings = global_settings
    
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=120, global_settings=global_settings)
    
    if not feb_result:
        print("❌ FAILED to plan February 2026 with locked constraints!")
        print("   This means the rotation continuity is broken!")
        return
    
    feb_assignments, feb_special_functions, _ = feb_result
    print(f"✓ February planned successfully: {len(feb_assignments)} assignments")
    
    # Verify that locked days are respected
    violations = []
    for assignment in feb_assignments:
        if assignment.date in [a.date for a in feb_days_from_jan]:
            # Check if this assignment matches what was planned in January
            jan_assignment = next((a for a in feb_days_from_jan if a.date == assignment.date and a.employee_id == assignment.employee_id), None)
            if jan_assignment and jan_assignment.shift_type_id != assignment.shift_type_id:
                violations.append(f"Date {assignment.date}: Jan planned shift {jan_assignment.shift_type_id}, Feb changed to {assignment.shift_type_id}")
    
    if violations:
        print(f"\n❌ ROTATION CONTINUITY VIOLATED! {len(violations)} conflicts:")
        for v in violations:
            print(f"  - {v}")
    else:
        print(f"\n✓ ROTATION CONTINUITY MAINTAINED!")
        print(f"  All {len(feb_days_from_jan)} days from January planning were respected in February")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_cross_month_continuity()
