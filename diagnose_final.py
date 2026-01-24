#!/usr/bin/env python3
"""
Detailed diagnostic to identify the root cause of infeasibility
"""

from datetime import date
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
import subprocess
import sqlite3

def setup_test_data():
    """Initialize database with test data"""
    print("Initializing test database...")
    subprocess.run(["rm", "-f", "dienstplan.db"], check=False)
    result = subprocess.run(["python3", "db_init.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False

    conn = sqlite3.connect("dienstplan.db")
    cursor = conn.cursor()

    # Create 3 teams
    teams_data = [(2, "Team Alpha"), (3, "Team Beta"), (4, "Team Gamma")]
    for team_id, team_name in teams_data:
        cursor.execute("INSERT OR IGNORE INTO Teams (Id, Name) VALUES (?, ?)", (team_id, team_name))

    # Create 15 employees (5 per team)
    employees_data = [
        (17, "Max", "Müller", "1001", "max@test.de", 2),
        (18, "Anna", "Schmidt", "1002", "anna@test.de", 2),
        (19, "Peter", "Weber", "1003", "peter@test.de", 2),
        (20, "Julia", "Becker", "1004", "julia@test.de", 2),
        (21, "Tom", "Wagner", "1005", "tom@test.de", 2),
        (22, "Lisa", "Meyer", "1006", "lisa@test.de", 3),
        (23, "Daniel", "Koch", "1007", "daniel@test.de", 3),
        (24, "Sarah", "Hoffmann", "1008", "sarah@test.de", 3),
        (25, "Michael", "Schulz", "1009", "michael@test.de", 3),
        (26, "Laura", "Bauer", "1010", "laura@test.de", 3),
        (27, "Markus", "Richter", "1011", "markus@test.de", 4),
        (28, "Stefanie", "Klein", "1012", "stefanie@test.de", 4),
        (29, "Christian", "Neumann", "1013", "christian@test.de", 4),
        (30, "Nicole", "Schröder", "1014", "nicole@test.de", 4),
        (31, "Andreas", "Wolf", "1015", "andreas@test.de", 4),
    ]

    for emp_id, vorname, name, personalnummer, email, team_id in employees_data:
        cursor.execute("""
            INSERT OR IGNORE INTO Employees 
            (Id, Vorname, Name, Personalnummer, Email, TeamId, PasswordHash, IsActive)
            VALUES (?, ?, ?, ?, ?, ?, 'dummy', 1)
        """, (emp_id, vorname, name, personalnummer, email, team_id))

    conn.commit()
    conn.close()
    print("✓ Test data created\n")
    return True

def analyze_january_problem():
    """Detailed analysis of the January 2026 planning problem"""
    print("\n" + "="*80)
    print("DETAILED PROBLEM ANALYSIS FOR JANUARY 2026")
    print("="*80 + "\n")
    
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday
    
    employees, teams, absences, shift_types = load_from_database("dienstplan.db")
    
    days = (end_date - start_date).days + 1
    num_weeks = days / 7.0
    
    print(f"1. BASIC CONFIGURATION")
    print(f"{'='*80}")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  Total days: {days}")
    print(f"  Calendar weeks: ~{num_weeks:.1f} (start: {start_date.strftime('%A')}, end: {end_date.strftime('%A')})")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len([e for e in employees if e.team_id])} ({len([e for e in employees if e.team_id]) // len(teams)} per team)")
    print()
    
    print(f"2. SHIFT REQUIREMENTS")
    print(f"{'='*80}")
    for st in shift_types:
        print(f"  {st.name} ({st.code}):")
        print(f"    Hours per shift: {st.hours}h")
        print(f"    Weekday staffing: {st.min_staff_weekday}-{st.max_staff_weekday} workers")
        print(f"    Weekend staffing: {st.min_staff_weekend}-{st.max_staff_weekend} workers")
        print(f"    Target weekly hours: {st.weekly_working_hours}h")
    print()
    
    # Count weekdays vs weekends
    num_weekdays = sum(1 for d in range(days) if (start_date + __import__('datetime').timedelta(d)).weekday() < 5)
    num_weekends = days - num_weekdays
    
    print(f"3. DAILY STAFFING REQUIREMENTS")
    print(f"{'='*80}")
    print(f"  Weekdays ({num_weekdays} days):")
    for st in shift_types:
        print(f"    {st.code}: {st.min_staff_weekday}-{st.max_staff_weekday} workers per day")
    print(f"  Weekends ({num_weekends} days):")
    for st in shift_types:
        print(f"    {st.code}: {st.min_staff_weekend}-{st.max_staff_weekend} workers per day")
    print()
    
    #Calculate total person-days needed
    min_person_days_weekday = num_weekdays * sum(st.min_staff_weekday for st in shift_types)
    max_person_days_weekday = num_weekdays * sum(st.max_staff_weekday for st in shift_types)
    min_person_days_weekend = num_weekends * sum(st.min_staff_weekend for st in shift_types)
    max_person_days_weekend = num_weekends * sum(st.max_staff_weekend for st in shift_types)
    
    total_min_person_days = min_person_days_weekday + min_person_days_weekend
    total_max_person_days = max_person_days_weekday + max_person_days_weekend
    
    print(f"4. TOTAL STAFFING DEMAND")
    print(f"{'='*80}")
    print(f"  Minimum person-days needed: {total_min_person_days}")
    print(f"    Weekdays: {min_person_days_weekday}")
    print(f"    Weekends: {min_person_days_weekend}")
    print(f"  Maximum person-days available: {total_max_person_days}")
    print(f"    Weekdays: {max_person_days_weekday}")
    print(f"    Weekends: {max_person_days_weekend}")
    print()
    
    num_employees = len([e for e in employees if e.team_id])
    
    # Monthly hours requirement
    monthly_hours = st.weekly_working_hours * (days / 7.0)
    min_days_per_employee = monthly_hours / 8.0  # 8 hours per shift
    total_min_employee_days = num_employees * min_days_per_employee
    
    print(f"5. EMPLOYEE WORKING HOURS CONSTRAINT")
    print(f"{'='*80}")
    print(f"  Target: {st.weekly_working_hours}h per week")
    print(f"  For {num_weeks:.1f} weeks: {monthly_hours:.1f}h total")
    print(f"  At 8h per shift: {min_days_per_employee:.1f} days minimum per employee")
    print(f"  Total minimum person-days (all employees): {total_min_employee_days:.1f}")
    print()
    
    print(f"6. SUPPLY vs DEMAND BALANCE")
    print(f"{'='*80}")
    balance_check_1 = total_min_employee_days <= total_max_person_days
    balance_check_2 = total_min_person_days <= total_min_employee_days
    
    print(f"  Check 1: Can employees meet demand with max capacity?")
    print(f"    Employee minimum days ({total_min_employee_days:.1f}) <= Max capacity ({total_max_person_days})")
    print(f"    Result: {'✓ YES' if balance_check_1 else '✗ NO - NOT ENOUGH CAPACITY'}")
    print()
    print(f"  Check 2: Can demand be met with employee minimum?")
    print(f"    Minimum demand ({total_min_person_days}) <= Employee minimum ({total_min_employee_days:.1f})")
    print(f"    Result: {'✓ YES' if balance_check_2 else '✗ NO - EMPLOYEES MUST WORK MORE'}")
    print()
    
    print(f"7. TEAM ROTATION CONSTRAINT")
    print(f"{'='*80}")
    print(f"  Rotation pattern: F → N → S (3-week cycle)")
    print(f"  With {len(teams)} teams and {num_weeks:.1f} weeks:")
    full_cycles = num_weeks / 3
    print(f"    ~{full_cycles:.2f} complete rotation cycles")
    print(f"    Each team does each shift ~{full_cycles:.2f} times")
    print()
    
    # Analyze per-shift allocation
    weeks_per_shift_per_team = num_weeks / 3
    days_per_shift_per_team = weeks_per_shift_per_team * 7
    
    print(f"  Per team, per shift type:")
    print(f"    Weeks: ~{weeks_per_shift_per_team:.2f}")
    print(f"    Days: ~{days_per_shift_per_team:.2f}")
    print()
    
    members_per_team = num_employees // len(teams)
    
    for st in shift_types:
        weekday_days = days_per_shift_per_team * (num_weekdays / days)
        weekend_days = days_per_shift_per_team * (num_weekends / days)
        
        min_needed_weekday = st.min_staff_weekday * weekday_days
        max_available_weekday = members_per_team * weekday_days
        min_needed_weekend = st.min_staff_weekend * weekend_days
        max_available_weekend = members_per_team * weekend_days
        
        print(f"  {st.code} shift analysis per team:")
        print(f"    Weekdays ({weekday_days:.1f} days): need {min_needed_weekday:.1f} person-days, have {max_available_weekday:.1f}")
        print(f"    Weekends ({weekend_days:.1f} days): need {min_needed_weekend:.1f} person-days, have {max_available_weekend:.1f}")
        
        if min_needed_weekday > max_available_weekday or min_needed_weekend > max_available_weekend:
            print(f"    ⚠️  PROBLEM: Team cannot provide enough workers!")
            print(f"        → {members_per_team} members cannot cover min requirements of {st.min_staff_weekday}/{st.min_staff_weekend}")
        print()
    
    print(f"8. KEY CONSTRAINT INTERACTIONS")
    print(f"{'='*80}")
    print(f"  ❌ IDENTIFIED CONFLICT:")
    print(f"     Team rotation forces each team to work N shift for ~{weeks_per_shift_per_team:.1f} weeks")
    print(f"     N shift requires minimum {shift_types[2].min_staff_weekday} workers on weekdays")
    print(f"     But teams only have {members_per_team} members")
    print(f"     {members_per_team - shift_types[2].min_staff_weekday} members must work cross-team to meet hours")
    print()
    print(f"     With minimum hours constraint requiring {min_days_per_employee:.1f} days per employee,")
    print(f"     and the N-shift team only needing {shift_types[2].min_staff_weekday} workers,")
    print(f"     the remaining {members_per_team - shift_types[2].min_staff_weekday} must find enough cross-team days.")
    print()
    print(f"     Cross-team capacity: Other teams' max staffing - their own needs")
    print(f"     This becomes constrained when all teams rotate through similar positions")
    print(f"     over a {num_weeks:.1f}-week period with partial weeks at start/end.")
    print()

def test_different_periods():
    """Test with different time periods to find feasibility threshold"""
    print("\n" + "="*80)
    print("TESTING DIFFERENT TIME PERIODS")
    print("="*80 + "\n")
    
    test_cases = [
        ("1 week (Mon-Sun)", date(2026, 1, 5), date(2026, 1, 11)),
        ("2 weeks (Mon-Sun)", date(2026, 1, 5), date(2026, 1, 18)),
        ("3 weeks (Mon-Sun)", date(2026, 1, 5), date(2026, 1, 25)),
        ("4 weeks (Mon-Sun)", date(2026, 1, 5), date(2026, 2, 1)),
        ("Full January", date(2026, 1, 1), date(2026, 1, 31)),
    ]
    
    for name, start_date, end_date in test_cases:
        days = (end_date - start_date).days + 1
        print(f"{name:.<45} {days:>2} days ... ", end='', flush=True)
        
        employees, teams, absences, shift_types = load_from_database("dienstplan.db")
        global_settings = load_global_settings("dienstplan.db")

        planning_model = create_shift_planning_model(
            employees, teams, start_date, end_date, absences, shift_types=shift_types
        )

        result = solve_shift_planning(planning_model, time_limit_seconds=60, global_settings=global_settings)
        
        if result:
            print("✓ FEASIBLE")
        else:
            print("✗ INFEASIBLE")

def main():
    if not setup_test_data():
        return
    
    # Detailed analysis
    analyze_january_problem()
    
    # Test different periods
    test_different_periods()

if __name__ == "__main__":
    main()
