"""
Comprehensive analysis of why shift planning is INFEASIBLE for January 2026.
Analyzes the team rotation constraint in detail.
"""

from datetime import date, timedelta
from calendar import monthrange
import math

def analyze_team_rotation_feasibility():
    """
    Analyze the F → N → S team rotation pattern and its impact on feasibility.
    """
    print("=" * 80)
    print("TEAM ROTATION FEASIBILITY ANALYSIS FOR JANUARY 2026")
    print("=" * 80)
    
    # Configuration
    num_teams = 3
    num_employees_per_team = 5
    num_employees = num_teams * num_employees_per_team
    shift_types = ['F', 'S', 'N']
    weekly_hours = 48.0
    shift_hours = 8.0
    
    # January 2026 calendar
    year = 2026
    month = 1
    _, num_days = monthrange(year, month)
    first_day = date(year, month, 1)
    
    # Count weekdays and weekends
    dates = [date(year, month, day) for day in range(1, num_days + 1)]
    weekdays = [d for d in dates if d.weekday() < 5]  # Mon-Fri
    weekends = [d for d in dates if d.weekday() >= 5]  # Sat-Sun
    
    print(f"\n1. BASIC CONFIGURATION")
    print(f"   Teams: {num_teams}")
    print(f"   Employees per team: {num_employees_per_team}")
    print(f"   Total employees: {num_employees}")
    print(f"   Shift types: {', '.join(shift_types)}")
    print(f"   Days in January: {num_days}")
    print(f"   Weekdays (Mon-Fri): {len(weekdays)}")
    print(f"   Weekend days (Sat-Sun): {len(weekends)}")
    print(f"   First day: {first_day.strftime('%A, %B %d, %Y')}")
    
    # Calculate hours requirements
    num_weeks = num_days / 7.0
    monthly_hours = weekly_hours * num_weeks
    days_needed = monthly_hours / shift_hours
    
    print(f"\n2. HOURS REQUIREMENTS")
    print(f"   Weekly target: {weekly_hours}h")
    print(f"   Shift duration: {shift_hours}h")
    print(f"   Number of weeks: {num_weeks:.2f}")
    print(f"   Monthly target: {monthly_hours:.1f}h per employee")
    print(f"   Days needed: {days_needed:.1f} days per employee")
    
    # Team rotation analysis
    print(f"\n3. TEAM ROTATION CONSTRAINT")
    print(f"   Pattern: F → N → S (weekly rotation)")
    print(f"   Rule: Each team works EXACTLY ONE shift per week")
    print(f"   Rule: All {num_employees_per_team} members of a team work TOGETHER")
    
    # Calculate how many shifts each team works per month
    weeks_in_month = math.ceil(num_days / 7.0)
    print(f"\n   Weeks in January (ceiling): {weeks_in_month}")
    
    # Week boundaries
    print(f"\n   Week breakdown:")
    week_num = 1
    current_date = first_day
    weeks = []
    while current_date <= dates[-1]:
        week_start = current_date
        week_end = min(current_date + timedelta(days=6), dates[-1])
        week_days = (week_end - week_start).days + 1
        week_weekdays = sum(1 for d in [week_start + timedelta(days=i) for i in range(week_days)] if d.weekday() < 5)
        week_weekends = week_days - week_weekdays
        weeks.append({
            'num': week_num,
            'start': week_start,
            'end': week_end,
            'days': week_days,
            'weekdays': week_weekdays,
            'weekends': week_weekends
        })
        print(f"   Week {week_num}: {week_start} to {week_end} ({week_days} days: {week_weekdays} weekdays, {week_weekends} weekend)")
        current_date = week_end + timedelta(days=1)
        week_num += 1
    
    num_weeks_actual = len(weeks)
    
    # Calculate team assignments
    print(f"\n4. TEAM SHIFT ASSIGNMENTS")
    print(f"   With {num_teams} teams and {num_weeks_actual} weeks:")
    
    rotation = ['F', 'N', 'S']
    for week_idx, week in enumerate(weeks):
        print(f"\n   Week {week['num']} ({week['start']} to {week['end']}):")
        for team_idx in range(num_teams):
            shift = rotation[(week_idx + team_idx) % len(rotation)]
            print(f"      Team {team_idx + 1}: {shift} shift ({num_employees_per_team} employees)")
    
    # Calculate work days per employee
    print(f"\n5. WORK DAYS PER EMPLOYEE")
    print(f"   Each team works in {num_weeks_actual} weeks")
    print(f"   Each week, a team's shift operates on certain days")
    
    # Key insight: How many days does each shift operate per week?
    print(f"\n   Shift operation days:")
    print(f"   - F (Früh): 05:45-13:45 = operates all 7 days/week")
    print(f"   - S (Spät): 13:45-21:45 = operates all 7 days/week")
    print(f"   - N (Nacht): 21:45-05:45 = operates all 7 days/week")
    print(f"   (From STANDARD_SHIFT_TYPES configuration)")
    
    # Calculate max possible work days
    print(f"\n6. MAXIMUM POSSIBLE WORK DAYS")
    total_work_days = 0
    for week_idx, week in enumerate(weeks):
        print(f"\n   Week {week['num']}:")
        for team_idx in range(num_teams):
            shift = rotation[(week_idx + team_idx) % len(rotation)]
            # All shifts operate 7 days/week
            days_available = week['days']
            total_work_days += days_available * num_employees_per_team
            print(f"      Team {team_idx + 1} on {shift}: {days_available} days × {num_employees_per_team} employees = {days_available * num_employees_per_team} employee-days")
    
    print(f"\n   Total employee-days available: {total_work_days}")
    total_needed = num_employees * days_needed
    print(f"   Total employee-days needed: {total_needed:.1f}")
    print(f"   Difference: {total_work_days - total_needed:.1f}")
    
    if total_work_days >= total_needed:
        print(f"   ✓ SUFFICIENT capacity with team rotation")
    else:
        print(f"   ✗ INSUFFICIENT capacity - need {total_needed - total_work_days:.1f} more employee-days")
    
    # Staffing constraints impact
    print(f"\n7. STAFFING CONSTRAINTS IMPACT")
    print(f"   Current configuration (from STANDARD_SHIFT_TYPES):")
    print(f"   - Weekday: min=4, max=20")
    print(f"   - Weekend: min=2, max=20")
    
    print(f"\n   When Team X is assigned to shift Y in week Z:")
    print(f"   - All {num_employees_per_team} members work that shift")
    print(f"   - They can work UP TO the max_staff limit per day")
    print(f"   - But need AT LEAST min_staff per day")
    
    print(f"\n   Potential conflict:")
    print(f"   - If min_staff_weekday = 4 and team has 5 members")
    print(f"   - Weekday requires at least 4 employees")
    print(f"   - Team has 5 employees available")
    print(f"   - ✓ No conflict (4 ≤ 5 ≤ 20)")
    
    print(f"\n   - If min_staff_weekend = 2 and team has 5 members")
    print(f"   - Weekend requires at least 2 employees")
    print(f"   - Team has 5 employees available")
    print(f"   - ✓ No conflict (2 ≤ 5 ≤ 20)")
    
    # Calculate actual work distribution
    print(f"\n8. ACTUAL WORK DISTRIBUTION ANALYSIS")
    print(f"   Each employee needs {days_needed:.1f} days of work")
    print(f"   With team rotation, employee can work:")
    print(f"   - Their team's assigned shift in a given week")
    print(f"   - ALL days that shift operates (7 days/week)")
    print(f"   - OR cross-team as a 'Springer' to other shifts")
    
    # Calculate if employees can reach target with their team only
    max_days_per_employee = num_weeks_actual * 7  # Max if working every day in assigned weeks
    print(f"\n   Maximum days if working EVERY day in assigned weeks: {max_days_per_employee}")
    print(f"   Target days needed: {days_needed:.1f}")
    
    if days_needed <= max_days_per_employee:
        print(f"   ✓ Target is reachable")
    else:
        print(f"   ✗ Target is NOT reachable - need cross-team work")
    
    # THE KEY ISSUE
    print(f"\n9. THE INFEASIBILITY ISSUE")
    print(f"   The problem is likely NOT with simple capacity.")
    print(f"   The issue is with the COMBINATION of constraints:")
    print(f"\n   a) Team rotation (F → N → S weekly)")
    print(f"   b) Hours target ({monthly_hours:.1f}h = {days_needed:.1f} days)")
    print(f"   c) Staffing min/max (weekday: 4-20, weekend: 2-20)")
    print(f"   d) Rest time (11h between shifts)")
    print(f"   e) Consecutive work (max 6 days)")
    print(f"   f) Fairness objectives (weekend/night distribution)")
    
    print(f"\n   Specific conflict scenario:")
    print(f"   - Employee needs {days_needed:.1f} days")
    print(f"   - Only {len(weekdays)} weekdays + {len(weekends)} weekend days = {num_days} days total")
    print(f"   - Employee must work {days_needed:.1f}/{num_days} = {(days_needed/num_days)*100:.1f}% of days")
    print(f"   - But team rotation + consecutive work limits may conflict")
    
    print(f"\n   Example conflict:")
    print(f"   - Week 1: Team 1 on F shift (7 days available)")
    print(f"   - If employee works 6 consecutive days (max), needs 1 day rest")
    print(f"   - Week 2: Team 1 on N shift (needs to work more days)")
    print(f"   - But rest time constraint may force days off")
    print(f"   - Result: Can't reach {days_needed:.1f} days in {num_weeks_actual} weeks")
    
    # Recommendations
    print(f"\n10. RECOMMENDATIONS TO FIX INFEASIBILITY")
    print(f"\n   Option 1: Reduce weekly hours target")
    max_feasible_days = num_days - math.ceil(num_days / 7.0)  # Accounting for rest days
    max_feasible_hours = max_feasible_days * shift_hours
    max_weekly_hours = max_feasible_hours / num_weeks
    print(f"      Reduce from {weekly_hours}h/week to ≤{max_weekly_hours:.1f}h/week")
    print(f"      This would require ≤{max_feasible_days} days per employee")
    
    print(f"\n   Option 2: Increase max consecutive work days")
    print(f"      Increase from 6 to 7 or more days")
    print(f"      Allows employees to work more days per week")
    
    print(f"\n   Option 3: Relax rest time constraints")
    print(f"      Allow shorter rest periods (currently 11h)")
    print(f"      Or allow cross-shift work with careful scheduling")
    
    print(f"\n   Option 4: Extend planning period")
    print(f"      Plan for more than {num_days} days")
    print(f"      Distribute hours over longer period")
    
    print(f"\n   Option 5: Allow more flexible team rotation")
    print(f"      Instead of strict F → N → S weekly rotation")
    print(f"      Allow teams to skip weeks or adjust pattern")
    
    # Calculate recommended max staffing
    print(f"\n11. RECOMMENDED STAFFING CONFIGURATION")
    avg_staff_needed = (num_employees * days_needed) / num_days
    print(f"   Average staff per day: {avg_staff_needed:.1f}")
    print(f"   Recommended max_staff_weekday: {math.ceil(avg_staff_needed * 1.2)}")
    print(f"   Recommended max_staff_weekend: {math.ceil(avg_staff_needed * 1.2)}")
    print(f"   (20% buffer for flexibility)")
    
    print(f"\n" + "=" * 80)
    print(f"CONCLUSION")
    print(f"=" * 80)
    print(f"Mathematical capacity: {'SUFFICIENT' if total_work_days >= total_needed else 'INSUFFICIENT'}")
    print(f"Expected solver result: INFEASIBLE")
    print(f"Root cause: Combination of team rotation, consecutive work limit, and rest time constraints")
    print(f"Primary fix: Reduce weekly_working_hours from 48h to ~{max_weekly_hours:.0f}h")
    print(f"            OR increase max_consecutive_days from 6 to 7+")
    print(f"=" * 80)

if __name__ == "__main__":
    analyze_team_rotation_feasibility()
