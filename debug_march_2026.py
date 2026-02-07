"""
Debug script to understand the March 2026 INFEASIBLE issue.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType

# March 2026 planning period
start_date = date(2026, 3, 1)  # Sunday
end_date = date(2026, 3, 31)  # Tuesday

# Extended to complete weeks (Monday to Sunday)
extended_start = date(2026, 2, 23)  # Monday before March 1
extended_end = date(2026, 4, 5)    # Sunday after March 31

# Calculate weeks
weeks = []
current = extended_start
while current <= extended_end:
    week = []
    for i in range(7):
        if current <= extended_end:
            week.append(current)
        current += timedelta(days=1)
    if week:
        weeks.append(week)

print("=" * 80)
print("MARCH 2026 INFEASIBILITY ANALYSIS")
print("=" * 80)
print()

print(f"Planning Period: {start_date} to {end_date} (31 days)")
print(f"Extended Period: {extended_start} to {extended_end} ({(extended_end - extended_start).days + 1} days)")
print(f"Number of weeks: {len(weeks)}")
print()

# Shift configuration
shift_types = {
    "F": {"hours": 8, "min_weekday": 4, "max_weekday": 8},
    "S": {"hours": 8, "min_weekday": 3, "max_weekday": 6},
    "N": {"hours": 8, "min_weekday": 3, "max_weekday": 3},  # ← KEY CONSTRAINT
}

# Team configuration
num_teams = 3
team_size = 5
total_employees = num_teams * team_size

print(f"Teams: {num_teams}")
print(f"Team size: {team_size} members")
print(f"Total employees: {total_employees}")
print()

print("Shift Configuration:")
for shift, config in shift_types.items():
    print(f"  {shift}: {config['hours']}h, min={config['min_weekday']}, max={config['max_weekday']}")
print()

# Rotation pattern: F → N → S
rotation = ["F", "N", "S"]
print(f"Rotation: {' → '.join(rotation)} (3-week cycle)")
print()

# Analyze rotation over 6 weeks
print("Team Rotation Schedule (6 weeks):")
print("Week | " + " | ".join([f"Team {i+1}" for i in range(num_teams)]))
print("-----|" + "|".join(["-" * 8 for _ in range(num_teams)]))

for week_idx in range(len(weeks)):
    row = f"  {week_idx}  |"
    for team_idx in range(num_teams):
        rotation_idx = (week_idx + team_idx) % len(rotation)
        shift = rotation[rotation_idx]
        row += f"   {shift}    |"
    print(row)

print()

# Calculate hours per employee
print("Hours Analysis per Employee:")
print()

# Count how many weeks each team spends on each shift
n_weeks_per_team = sum(1 for w in range(len(weeks)) 
                       for t in range(num_teams) 
                       if rotation[(w + t) % len(rotation)] == "N") // num_teams

f_weeks_per_team = sum(1 for w in range(len(weeks)) 
                       for t in range(num_teams) 
                       if rotation[(w + t) % len(rotation)] == "F") // num_teams

s_weeks_per_team = sum(1 for w in range(len(weeks)) 
                       for t in range(num_teams) 
                       if rotation[(w + t) % len(rotation)] == "S") // num_teams

print(f"Each team works:")
print(f"  F shift: {f_weeks_per_team} weeks")
print(f"  S shift: {s_weeks_per_team} weeks")
print(f"  N shift: {n_weeks_per_team} weeks")
print()

# Calculate maximum hours during N weeks
# N max = 3, but team has 5 members, so only 3 can be active per day
n_shift_max = shift_types["N"]["max_weekday"]
days_per_week = 7

# During N week, team has 5 members but only 3 can be active per day
# So total team-hours = 7 days × 8h × 3 staff = 168 team-hours
# Distributed among 5 members = 168 / 5 = 33.6h per member
n_week_hours_per_member = (days_per_week * shift_types["N"]["hours"] * n_shift_max) / team_size

# During F or S weeks, all 5 members can work
# Max hours = 7 days × 8h = 56h per member
fs_week_hours_per_member = days_per_week * shift_types["F"]["hours"]

print("Maximum hours per employee:")
print(f"  During N week: {n_week_hours_per_member:.1f}h")
print(f"    (Team has {team_size} members, but N max is {n_shift_max}, so only {n_shift_max}/{team_size} can work)")
print(f"  During F week: {fs_week_hours_per_member:.1f}h")
print(f"  During S week: {fs_week_hours_per_member:.1f}h")
print()

# Calculate total maximum hours
total_max_hours = (n_weeks_per_team * n_week_hours_per_member + 
                   f_weeks_per_team * fs_week_hours_per_member + 
                   s_weeks_per_team * fs_week_hours_per_member)

print(f"Total maximum hours per employee over {len(weeks)} weeks:")
print(f"  {n_weeks_per_team} N weeks × {n_week_hours_per_member:.1f}h = {n_weeks_per_team * n_week_hours_per_member:.1f}h")
print(f"  {f_weeks_per_team} F weeks × {fs_week_hours_per_member:.1f}h = {f_weeks_per_team * fs_week_hours_per_member:.1f}h")
print(f"  {s_weeks_per_team} S weeks × {fs_week_hours_per_member:.1f}h = {s_weeks_per_team * fs_week_hours_per_member:.1f}h")
print(f"  TOTAL: {total_max_hours:.1f}h")
print()

# Check against minimum requirement
min_required_hours = 192
print(f"Minimum required hours: {min_required_hours}h (HARD constraint)")
print()

if total_max_hours >= min_required_hours:
    print(f"✓ FEASIBLE: {total_max_hours:.1f}h >= {min_required_hours}h")
    print()
    print("But wait... the solver is still failing!")
    print()
    print("Possible reasons:")
    print("1. Cross-team assignments may be restricted")
    print("2. Weekly shift consistency constraint (employee must work same shift all week)")
    print("3. Combination with other constraints creates infeasibility")
    print()
    print("Let me check if the problem is about STAFFING, not HOURS...")
    print()
    
    # Check staffing requirements
    print("Staffing Requirements Analysis:")
    print()
    
    total_days = (extended_end - extended_start).days + 1
    weekdays = sum(1 for i in range(total_days) if (extended_start + timedelta(days=i)).weekday() < 5)
    
    print(f"Total weekdays in extended period: {weekdays}")
    print()
    
    # For each weekday, we need min staff for each shift
    # But only ONE team per week is assigned to each shift
    # So team members MUST be active to meet minimum
    
    print("Daily Staffing:")
    print(f"  F shift needs: min {shift_types['F']['min_weekday']} staff per weekday")
    print(f"  S shift needs: min {shift_types['S']['min_weekday']} staff per weekday")
    print(f"  N shift needs: min {shift_types['N']['min_weekday']} staff per weekday")
    print()
    
    print("Team Assignment:")
    print(f"  Only 1 team (of {num_teams}) is assigned to each shift per week")
    print(f"  That team has {team_size} members")
    print()
    
    print("N Shift Problem:")
    print(f"  N needs min {shift_types['N']['min_weekday']} staff")
    print(f"  Team has {team_size} members")
    print(f"  {shift_types['N']['min_weekday']} <= {team_size} ✓ (team can provide minimum)")
    print()
    print(f"  BUT N max is {shift_types['N']['max_weekday']} staff")
    print(f"  So only {shift_types['N']['max_weekday']} of {team_size} members can be ACTIVE per day")
    print(f"  The other {team_size - shift_types['N']['max_weekday']} must be INACTIVE")
    print()
    print("  Those inactive members during N week:")
    print("    - Cannot work their team shift (N is full)")
    print("    - Must use cross-team shifts to meet 192h minimum")
    print("    - Cross-team shifts have CAPACITY constraints")
    print()
    
    # Check if cross-team can absorb the overflow
    print("Cross-Team Capacity Check:")
    print()
    
    # During an N week, one team has N shift
    # The other 2 teams have F and S
    # F max = 8, but team provides 5, so 3 slots free
    # S max = 6, but team provides 5, so 1 slot free
    # Total cross-team capacity = 3 + 1 = 4 slots per day
    
    # N team has 2 inactive members who need cross-team work
    # 2 < 4, so should be feasible... unless...
    
    f_slots_per_day = shift_types['F']['max_weekday'] - team_size  # 8 - 5 = 3
    s_slots_per_day = shift_types['S']['max_weekday'] - team_size  # 6 - 5 = 1
    n_inactive_per_day = team_size - shift_types['N']['max_weekday']  # 5 - 3 = 2
    
    print(f"  When one team is on N:")
    print(f"    - F team: {team_size} members working, {f_slots_per_day} slots free (max={shift_types['F']['max_weekday']})")
    print(f"    - S team: {team_size} members working, {s_slots_per_day} slot free (max={shift_types['S']['max_weekday']})")
    print(f"    - N team: {shift_types['N']['max_weekday']} active, {n_inactive_per_day} inactive")
    print(f"    - Total cross-team capacity: {f_slots_per_day + s_slots_per_day} slots")
    print(f"    - Need to place: {n_inactive_per_day} inactive N workers")
    print()
    
    if n_inactive_per_day <= f_slots_per_day + s_slots_per_day:
        print(f"  ✓ {n_inactive_per_day} <= {f_slots_per_day + s_slots_per_day} (sufficient capacity)")
        print()
        print("  So capacity exists... but there's another constraint!")
        print()
        print("CRITICAL INSIGHT:")
        print("  The 'weekly shift consistency' constraint requires:")
        print("  'Employees must work the SAME shift type throughout each week'")
        print()
        print("  This means:")
        print("  - If an N-team member is INACTIVE on Monday (N is full)")
        print("  - They can do cross-team on Tuesday (e.g., F shift)")
        print("  - But then they must do F for the ENTIRE WEEK")
        print("  - They can't switch back to N on Wednesday!")
        print()
        print("  Combined with the 192h minimum requirement:")
        print("  - N-team inactive members MUST do cross-team ALL WEEK")
        print("  - But cross-team capacity (4 slots/day) may not be enough")
        print("  - If 2 N-members need F or S ALL WEEK LONG")
        print("  - And those shifts are already staffed by their teams")
        print("  - The solver runs out of combinations!")
        print()
        print("ROOT CAUSE HYPOTHESIS:")
        print("  The minimum 192h constraint + N max=3 constraint + weekly consistency")
        print("  creates a situation where inactive N-team members can't find a")
        print("  consistent weekly shift pattern that meets 192h without violating")
        print("  staffing or consistency constraints.")
    else:
        print(f"  ✗ {n_inactive_per_day} > {f_slots_per_day + s_slots_per_day} (INSUFFICIENT capacity)")
        print()
        print("ROOT CAUSE:")
        print("  Not enough cross-team capacity to place inactive N-team members!")
else:
    print(f"✗ INFEASIBLE: {total_max_hours:.1f}h < {min_required_hours}h")
    print()
    print("ROOT CAUSE:")
    print("  Even with maximum utilization, employees cannot reach 192h minimum!")
    print("  This is because N shift max (3) limits team member participation")
    print("  during N weeks, reducing total available hours below the requirement.")
