#!/usr/bin/env python3
"""
Test shift planning for January 2026 with COMPLETE WEEKS extension

This test extends the planning period to complete weeks (Mon-Sun) on both ends,
which is what the web API does automatically.
"""

from datetime import date, timedelta
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
import subprocess

def extend_to_complete_weeks(start_date: date, end_date: date) -> tuple:
    """Extend dates to complete Mon-Sun weeks"""
    # Extend START backwards to Monday
    extended_start = start_date
    if start_date.weekday() != 0:  # Not Monday
        days_since_monday = start_date.weekday()
        extended_start = start_date - timedelta(days=days_since_monday)
    
    # Extend END forward to Sunday
    extended_end = end_date
    if end_date.weekday() != 6:  # Not Sunday
        days_until_sunday = 6 - end_date.weekday()
        extended_end = end_date + timedelta(days=days_until_sunday)
    
    return extended_start, extended_end

def test_january_extended():
    # Original January range
    original_start = date(2026, 1, 1)  # Thursday
    original_end = date(2026, 1, 31)   # Saturday
    
    # Extend to complete weeks
    start_date, end_date = extend_to_complete_weeks(original_start, original_end)

    print("="*80)
    print(f"Testing JANUARY 2026 with COMPLETE WEEKS:")
    print(f"  Original: {original_start} to {original_end} (31 days)")
    print(f"  Extended: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"  Extended days: {(end_date - start_date).days + 1}")
    print(f"  Complete weeks: {((end_date - start_date).days + 1) / 7:.1f}")
    print("="*80)
    print()

    # Initialize database
    print("Initializing database...")
    subprocess.run(["rm", "-f", "dienstplan.db"], check=False)
    result = subprocess.run(["python3", "db_init.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR initializing database: {result.stderr}")
        return False

    # Add test data
    print("Adding test data...")
    import sqlite3
    conn = sqlite3.connect("dienstplan.db")
    cursor = conn.cursor()

    # Create 3 teams
    teams_data = [
        (2, "Team Alpha"),
        (3, "Team Beta"),
        (4, "Team Gamma")
    ]

    for team_id, team_name in teams_data:
        cursor.execute("INSERT OR IGNORE INTO Teams (Id, Name) VALUES (?, ?)", (team_id, team_name))

    # Create 15 employees (5 per team)
    employees_data = [
        # Team Alpha (ID=2)
        (17, "Max", "Müller", "1001", "max@test.de", 2),
        (18, "Anna", "Schmidt", "1002", "anna@test.de", 2),
        (19, "Peter", "Weber", "1003", "peter@test.de", 2),
        (20, "Julia", "Becker", "1004", "julia@test.de", 2),
        (21, "Tom", "Wagner", "1005", "tom@test.de", 2),
        # Team Beta (ID=3)
        (22, "Lisa", "Meyer", "1006", "lisa@test.de", 3),
        (23, "Daniel", "Koch", "1007", "daniel@test.de", 3),
        (24, "Sarah", "Hoffmann", "1008", "sarah@test.de", 3),
        (25, "Michael", "Schulz", "1009", "michael@test.de", 3),
        (26, "Laura", "Bauer", "1010", "laura@test.de", 3),
        # Team Gamma (ID=4)
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

    print("✓ Test data created: 3 teams with 5 employees each\n")

    # Load data
    employees, teams, absences, shift_types = load_from_database("dienstplan.db")
    global_settings = load_global_settings("dienstplan.db")

    print(f"Loaded: {len(employees)} employees, {len(teams)} teams, {len(shift_types)} shift types")
    print(f"Shift types: {', '.join(st.code for st in shift_types)}")
    print(f"Max staffing: {', '.join(f'{st.code}={st.max_staff_weekday}' for st in shift_types)}\n")

    # Create planning model with EXTENDED dates
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )

    print("Model statistics:")
    planning_model.print_model_statistics()
    print()

    # Solve
    print("Attempting to solve...")
    result = solve_shift_planning(planning_model, time_limit_seconds=300, global_settings=global_settings)

    if result:
        print("\n" + "="*80)
        print("✅ SUCCESS! Planning is FEASIBLE for January 2026 (extended weeks)!")
        print("="*80)
        assignments, special_functions, complete_schedule = result
        
        print(f"\nTotal assignments: {len(assignments)}")
        
        # Filter to only January assignments
        january_assignments = [a for a in assignments 
                             if a.date >= original_start and a.date <= original_end]
        print(f"January-only assignments: {len(january_assignments)}")
        
        # Check employee hours
        from collections import defaultdict
        emp_hours = defaultdict(int)
        emp_days = defaultdict(int)
        
        for a in january_assignments:
            emp_hours[a.employee_id] += 8  # 8 hours per shift
            emp_days[a.employee_id] += 1
        
        print(f"\nEmployee hours for January (original month only):")
        print(f"{'Employee':<25} {'Hours':<10} {'Days':<10}")
        print("-" * 50)
        for emp_id in sorted(emp_hours.keys()):
            emp = next((e for e in employees if e.id == emp_id), None)
            if emp:
                print(f"{emp.vorname} {emp.name:<20} {emp_hours[emp_id]:>4}h      {emp_days[emp_id]:>3} days")
        
        print(f"\nAll {len([e for e in emp_hours if emp_hours[e] > 0])} employees have shift assignments in January")
        
        # Check if minimum hours met
        min_hours = 192
        below_min = [e for e in emp_hours if emp_hours[e] < min_hours]
        if below_min:
            print(f"\n⚠️  {len(below_min)} employees below {min_hours}h minimum")
        else:
            print(f"\n✅ All employees meet or exceed {min_hours}h minimum")
        
        return True
    else:
        print("\n" + "="*80)
        print("✗ INFEASIBLE for January 2026 (even with extended weeks)")
        print("="*80)
        return False

if __name__ == "__main__":
    success = test_january_extended()
    exit(0 if success else 1)
