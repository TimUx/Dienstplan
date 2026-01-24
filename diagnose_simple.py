#!/usr/bin/env python3
"""
Simpler diagnostic: Test by commenting out constraints one by one
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

def test_with_fewer_weeks():
    """Test with different time periods"""
    print("\n" + "="*80)
    print("TESTING DIFFERENT TIME PERIODS")
    print("="*80 + "\n")
    
    test_cases = [
        ("1 week", date(2026, 1, 6), date(2026, 1, 12)),   # Mon-Sun
        ("2 weeks", date(2026, 1, 6), date(2026, 1, 19)),  # Mon-Sun
        ("3 weeks", date(2026, 1, 6), date(2026, 1, 26)),  # Mon-Sun
        ("4 weeks", date(2026, 1, 6), date(2026, 2, 2)),   # Mon-Sun
        ("Full January (31 days)", date(2026, 1, 1), date(2026, 1, 31)),
    ]
    
    for name, start_date, end_date in test_cases:
        days = (end_date - start_date).days + 1
        print(f"\nTest: {name} ({days} days)")
        print(f"  Period: {start_date} to {end_date}")
        
        employees, teams, absences, shift_types = load_from_database("dienstplan.db")
        global_settings = load_global_settings("dienstplan.db")

        planning_model = create_shift_planning_model(
            employees, teams, start_date, end_date, absences, shift_types=shift_types
        )

        result = solve_shift_planning(planning_model, time_limit_seconds=60, global_settings=global_settings)
        
        if result:
            print(f"  ✓ FEASIBLE")
        else:
            print(f"  ✗ INFEASIBLE")

def analyze_problem_structure():
    """Analyze the mathematical structure of the problem"""
    print("\n" + "="*80)
    print("MATHEMATICAL PROBLEM ANALYSIS")
    print("="*80 + "\n")
    
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    employees, teams, absences, shift_types = load_from_database("dienstplan.db")
    
    # Count by shift type
    shift_requirements = {}
    for st in shift_types:
        shift_requirements[st.code] = {
            'min': st.min_staff,
            'max': st.max_staff,
            'hours': st.duration_hours,
            'weekly_hours': st.weekly_working_hours
        }
    
    days = (end_date - start_date).days + 1
    num_weeks = days / 7
    
    print(f"Configuration:")
    print(f"  Planning period: {days} days ({num_weeks:.1f} weeks)")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len([e for e in employees if e.team_id])}")
    print(f"  Employees per team: {len([e for e in employees if e.team_id]) // len(teams)}")
    print()
    
    print(f"Shift requirements per day:")
    for code, req in shift_requirements.items():
        print(f"  {code}: {req['min']}-{req['max']} workers, {req['hours']}h/shift, target: {req['weekly_hours']}h/week")
    print()
    
    # Calculate demand
    total_daily_min_demand = sum(req['min'] for req in shift_requirements.values())
    total_daily_max_demand = sum(req['max'] for req in shift_requirements.values())
    
    total_min_person_days = total_daily_min_demand * days
    total_max_person_days = total_daily_max_demand * days
    
    print(f"Demand analysis:")
    print(f"  Min workers per day: {total_daily_min_demand}")
    print(f"  Max workers per day: {total_daily_max_demand}")
    print(f"  Total min person-days needed: {total_min_person_days}")
    print(f"  Total max person-days available: {total_max_person_days}")
    print()
    
    # Calculate supply
    num_employees = len([e for e in employees if e.team_id])
    
    # With 48h/week target and 8h/day, each employee works 6 days/week
    target_days_per_week = 48 / 8
    total_target_person_days = num_employees * target_days_per_week * num_weeks
    
    # Minimum hours requirement: 192h/month = 24 days for 31-day month
    min_days_per_employee = 24
    total_min_person_days_supply = num_employees * min_days_per_employee
    
    print(f"Supply analysis:")
    print(f"  Employees: {num_employees}")
    print(f"  Target: {target_days_per_week} days/week = {target_days_per_week * num_weeks:.1f} days total per employee")
    print(f"  Minimum: {min_days_per_employee} days per employee (192h/month)")
    print(f"  Total target person-days: {total_target_person_days:.1f}")
    print(f"  Total min person-days: {total_min_person_days_supply}")
    print()
    
    print(f"Balance check:")
    if total_min_person_days_supply <= total_max_person_days:
        print(f"  ✓ Min supply ({total_min_person_days_supply}) <= Max capacity ({total_max_person_days})")
    else:
        print(f"  ✗ Min supply ({total_min_person_days_supply}) > Max capacity ({total_max_person_days})")
    
    if total_min_person_days <= total_min_person_days_supply:
        print(f"  ✓ Min demand ({total_min_person_days}) <= Min supply ({total_min_person_days_supply})")
    else:
        print(f"  ✗ Min demand ({total_min_person_days}) > Min supply ({total_min_person_days_supply})")
    
    # Team rotation constraint
    print(f"\nTeam rotation constraint:")
    print(f"  Each team rotates through F → N → S every 3 weeks")
    print(f"  With {len(teams)} teams and {num_weeks:.1f} weeks:")
    num_full_rotations = num_weeks / 3
    print(f"    ~{num_full_rotations:.1f} complete rotations")
    print(f"    Each team does each shift type ~{num_full_rotations:.1f} times")
    
    # Team constraints
    members_per_team = num_employees // len(teams)
    print(f"\nTeam-based constraints:")
    print(f"  {members_per_team} members per team")
    print(f"  When a team is on N shift (requires {shift_requirements['N']['min']}-{shift_requirements['N']['max']} workers):")
    print(f"    {members_per_team - shift_requirements['N']['max']} members must work cross-team")

def main():
    if not setup_test_data():
        return
    
    # Analyze the problem structure
    analyze_problem_structure()
    
    # Test with different time periods
    test_with_fewer_weeks()

if __name__ == "__main__":
    main()
