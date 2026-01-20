"""
Debug why minimum hours constraint causes INFEASIBLE.
Analyze the mathematical feasibility.
"""

# Configuration
num_employees_per_team = 5
num_teams = 3
num_days = 31
num_weeks = 31 / 7.0  # 4.43 weeks
weekly_hours = 40  # From STANDARD_SHIFT_TYPES
shift_hours = 8

# Requirements
min_staffing_weekday = 3
max_staffing_weekday = 5
min_staffing_weekend = 2
max_staffing_weekend = 3

# Calculate
expected_monthly_hours = weekly_hours * num_weeks
days_needed_per_employee = expected_monthly_hours / shift_hours

num_weekdays = sum(1 for d in range(31) if (d % 7) < 5)  # Rough estimate
num_weekend_days = 31 - num_weekdays

print("=" * 80)
print("FEASIBILITY ANALYSIS")
print("=" * 80)
print(f"\nConfiguration:")
print(f"  Teams: {num_teams}")
print(f"  Employees per team: {num_employees_per_team}")
print(f"  Total employees: {num_employees_per_team * num_teams}")
print(f"  Planning period: {num_days} days ({num_weeks:.2f} weeks)")
print(f"  Weekdays (approx): {num_weekdays}")
print(f"  Weekend days (approx): {num_weekend_days}")

print(f"\nHours requirement:")
print(f"  Weekly hours: {weekly_hours}h")
print(f"  Monthly hours: {expected_monthly_hours:.1f}h")
print(f"  Days needed per employee: {days_needed_per_employee:.1f} days")

print(f"\nStaffing constraints:")
print(f"  Weekday: min={min_staffing_weekday}, max={max_staffing_weekday}")
print(f"  Weekend: min={min_staffing_weekend}, max={max_staffing_weekend}")

# Team rotation analysis
print(f"\nTeam Rotation Analysis (F → N → S):")
print(f"  Each team works 1 shift per week")
print(f"  All 5 team members work the SAME shift that week")

# Calculate capacity
total_employee_days_available = num_employees_per_team * num_teams * num_days
total_employee_days_needed = num_employees_per_team * num_teams * days_needed_per_employee

# Rough estimate of shift slots (ignoring team rotation for now)
weekday_slots = num_weekdays * min_staffing_weekday  # Minimum slots
weekend_slots = num_weekend_days * min_staffing_weekend
total_min_slots = weekday_slots + weekend_slots

weekday_slots_max = num_weekdays * max_staffing_weekday
weekend_slots_max = num_weekend_days * max_staffing_weekend
total_max_slots = weekday_slots_max + weekend_slots_max

print(f"\nCapacity Analysis (simplified, ignoring rotation):")
print(f"  Total employee-days needed: {total_employee_days_needed:.1f}")
print(f"  Min shift slots available: {total_min_slots}")
print(f"  Max shift slots available: {total_max_slots}")
print(f"  Feasible: {total_employee_days_needed <= total_max_slots}")

# More detailed: With team rotation
print(f"\nTeam Rotation Impact:")
print(f"  With team rotation, each team works 1 shift per week")
print(f"  {num_teams} teams × {num_weeks:.1f} weeks ≈ {num_teams * num_weeks:.0f} team-weeks")
print(f"  But we have 3 shifts (F, N, S) rotating")
print(f"  So each week: Team 1=F, Team 2=N, Team 3=S (for example)")

# Key insight: Team members work TOGETHER
print(f"\nCritical Insight:")
print(f"  All 5 members of a team work the SAME shift in a given week")
print(f"  Staffing max={max_staffing_weekday} on weekdays")
print(f"  If all 5 want to work, but max is only 5, all CAN work!")
print(f"  But if employees need {days_needed_per_employee:.1f} days and there are only {num_weekdays} weekdays...")

print(f"\nWeekday Analysis:")
print(f"  Weekdays per week: ~5")
print(f"  With {num_weeks:.1f} weeks: {num_weekdays} weekdays total")
print(f"  If employee works all weekdays: {num_weekdays} days")
print(f"  Hours if working all weekdays: {num_weekdays * shift_hours}h")
print(f"  Target hours: {expected_monthly_hours:.1f}h")
print(f"  Shortfall if only weekdays: {expected_monthly_hours - num_weekdays * shift_hours:.1f}h")
print(f"  Need weekend days: {(expected_monthly_hours - num_weekdays * shift_hours) / shift_hours:.1f}")

print(f"\nConclusion:")
if days_needed_per_employee <= num_weekdays:
    print(f"  ✓ Feasible with just weekdays")
else:
    weekend_days_needed = days_needed_per_employee - num_weekdays
    print(f"  ✗ Need {weekend_days_needed:.1f} weekend days per employee")
    print(f"  Weekend constraint: max {max_staffing_weekend} employees per day")
    print(f"  Weekend days available: {num_weekend_days}")
    total_weekend_slots = num_weekend_days * max_staffing_weekend
    total_weekend_days_needed = num_employees_per_team * num_teams * weekend_days_needed
    print(f"  Total weekend slots needed: {total_weekend_days_needed:.1f}")
    print(f"  Total weekend slots available: {total_weekend_slots}")
    if total_weekend_days_needed <= total_weekend_slots:
        print(f"  ✓ Weekend capacity is sufficient")
    else:
        print(f"  ✗ Not enough weekend capacity!")
        print(f"  Deficit: {total_weekend_days_needed - total_weekend_slots:.1f} employee-days")

print("\n" + "=" * 80)
