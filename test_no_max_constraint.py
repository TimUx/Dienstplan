#!/usr/bin/env python3
"""
Test shift planning for January 2026 with NO maximum staffing constraint (max=99).
This tests whether removing the max constraint solves the infeasibility issue.
"""

from datetime import date
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
import subprocess
import sqlite3

def test_january_no_max():
    # Test with January 2026
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday

    print("="*80)
    print(f"Testing JANUARY 2026 with NO MAX STAFFING CONSTRAINT (max=99)")
    print(f"  Period: {start_date} ({start_date.strftime('%A')}) to {end_date} ({end_date.strftime('%A')})")
    print(f"  Days: 31")
    print("="*80)
    print()

    # Initialize database
    print("Initializing database...")
    subprocess.run(["rm", "-f", "dienstplan.db"], check=False)
    result = subprocess.run(["python3", "db_init.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR initializing database: {result.stderr}")
        return False

    # Modify shift types to have max=99 (no constraint)
    print("Modifying shift types to remove max constraint (setting max=99)...")
    conn = sqlite3.connect("dienstplan.db")
    cursor = conn.cursor()
    
    # Update all shift types to have max=99
    cursor.execute("""
        UPDATE ShiftTypes 
        SET MinStaffWeekday = CASE Code 
            WHEN 'F' THEN 4 
            WHEN 'S' THEN 3 
            WHEN 'N' THEN 3 
            ELSE MinStaffWeekday 
        END,
        MaxStaffWeekday = 99,
        MaxStaffWeekend = 99
    """)
    
    # Verify the update
    cursor.execute("SELECT Code, MinStaffWeekday, MaxStaffWeekday, MaxStaffWeekend FROM ShiftTypes")
    rows = cursor.fetchall()
    print("\nShift types configuration:")
    for code, min_wd, max_wd, max_we in rows:
        print(f"  {code}: min_weekday={min_wd}, max_weekday={max_wd}, max_weekend={max_we}")
    
    conn.commit()

    # Add test data
    print("\nAdding test data...")
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
    print("\nShift types loaded:")
    for st in shift_types:
        print(f"  {st.code}: min={st.min_staff_weekday}, max={st.max_staff_weekday}")
    print()

    # Create planning model
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )

    print("Model statistics:")
    planning_model.print_model_statistics()
    print()

    # Solve
    print("Attempting to solve with NO MAX CONSTRAINT...")
    print("(This may take up to 3 minutes...)")
    result = solve_shift_planning(planning_model, time_limit_seconds=180, global_settings=global_settings)

    if result:
        print("\n" + "="*80)
        print("✓ SUCCESS! Planning is FEASIBLE for January 2026!")
        print("="*80)
        print("\n🎉 CONCLUSION: Removing the max staffing constraint SOLVES the problem!")
        print("   The infeasibility was caused by the maximum staffing limits.")
        assignments, special_functions, complete_schedule = result
        
        print(f"\nTotal assignments: {len(assignments)}")
        
        # Check employee hours
        from collections import defaultdict
        emp_hours = defaultdict(int)
        emp_days = defaultdict(int)
        
        for a in assignments:
            emp_hours[a.employee_id] += 8  # 8 hours per shift
            emp_days[a.employee_id] += 1
        
        print(f"\nEmployee hours for January:")
        print(f"{'Employee':<25} {'Hours':<10} {'Days':<10}")
        print("-" * 50)
        total_hours = 0
        for emp_id in sorted(emp_hours.keys()):
            emp = next((e for e in employees if e.id == emp_id), None)
            if emp:
                print(f"{emp.vorname} {emp.name:<20} {emp_hours[emp_id]:>4}h      {emp_days[emp_id]:>3} days")
                total_hours += emp_hours[emp_id]
        
        avg_hours = total_hours / len(employees) if employees else 0
        print(f"\nAverage hours per employee: {avg_hours:.1f}h")
        print(f"All {len([e for e in emp_hours if emp_hours[e] > 0])} employees have shift assignments")
        
        # Analyze staffing levels
        print(f"\nAnalyzing actual staffing levels per shift:")
        shift_staffing = defaultdict(list)
        for a in assignments:
            key = (a.date, a.shift_type_id)
            if key not in shift_staffing:
                shift_staffing[key] = []
            shift_staffing[key].append(a.employee_id)
        
        shift_counts = {st.id: [] for st in shift_types}
        for (d, st_id), emps in shift_staffing.items():
            shift_counts[st_id].append(len(emps))
        
        for st in shift_types:
            counts = shift_counts[st.id]
            if counts:
                print(f"  {st.code}: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
        
        return True
    else:
        print("\n" + "="*80)
        print("✗ STILL INFEASIBLE even without max staffing constraint")
        print("="*80)
        print("\n❌ CONCLUSION: The max staffing constraint is NOT the root cause.")
        print("   The problem lies elsewhere (likely minimum hours + rotation pattern).")
        return False

if __name__ == "__main__":
    success = test_january_no_max()
    exit(0 if success else 1)
