"""
Analyze feasibility with 48h/week requirement.
"""

num_employees_per_team = 5
num_teams = 3
num_days = 31
num_weeks = 31 / 7.0  # 4.43 weeks
weekly_hours = 48  # User's requirement
shift_hours = 8

# Estimate weekdays/weekends
num_weekdays = 23  # Roughly 5/7 of 31
num_weekend_days = 8  # Roughly 2/7 of 31

min_staffing_weekend = 2
max_staffing_weekend = 3
max_consecutive = 6

print("=" * 80)
print("FEASIBILITY ANALYSIS WITH 48h/WEEK")
print("=" * 80)

expected_monthly_hours = weekly_hours * num_weeks
days_needed_per_employee = expected_monthly_hours / shift_hours

print(f"\nRequirements:")
print(f"  Weekly hours: {weekly_hours}h")
print(f"  Monthly hours: {expected_monthly_hours:.1f}h")
print(f"  Days needed per employee: {days_needed_per_employee:.1f} days")

print(f"\nBreakdown:")
print(f"  Total days: {num_days}")
print(f"  Weekdays: {num_weekdays}")
print(f"  Weekend days: {num_weekend_days}")

print(f"\nIf employee works ALL weekdays:")
weekday_hours = num_weekdays * shift_hours
print(f"  Hours from weekdays: {weekday_hours}h")
print(f"  Remaining needed: {expected_monthly_hours - weekday_hours:.1f}h")
weekend_days_needed = (expected_monthly_hours - weekday_hours) / shift_hours
print(f"  Weekend days needed: {weekend_days_needed:.1f}")

print(f"\nWeekend Constraint Analysis:")
print(f"  Weekend staffing max: {max_staffing_weekend} employees/day")
print(f"  Each employee needs: {weekend_days_needed:.1f} weekend days")
print(f"  Total weekend slots available: {num_weekend_days * max_staffing_weekend}")
total_weekend_days_needed = num_employees_per_team * num_teams * weekend_days_needed
print(f"  Total weekend days needed (all employees): {total_weekend_days_needed:.1f}")

if total_weekend_days_needed > num_weekend_days * max_staffing_weekend:
    print(f"\n❌ INFEASIBLE!")
    print(f"  Weekend capacity insufficient!")
    deficit = total_weekend_days_needed - (num_weekend_days * max_staffing_weekend)
    print(f"  Deficit: {deficit:.1f} employee-weekend-days")
    
    # Calculate required weekend max
    required_max = total_weekend_days_needed / num_weekend_days
    print(f"\n  Solution: Increase weekend max from {max_staffing_weekend} to {required_max:.1f}")
    print(f"  Rounded up: {int(required_max + 0.999)}")
else:
    print(f"\n✓ Feasible with current weekend max")

print("\n" + "=" * 80)
