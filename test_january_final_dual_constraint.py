#!/usr/bin/env python3
"""
FINAL TEST: January 2026 with Dual-Constraint System
Tests monthly shift planning with:
- 3 Teams × 5 Employees = 15 total
- 48h/week target
- HARD CONSTRAINT: >= 192h minimum
- SOFT CONSTRAINT: Target 213h (48÷7 × 31)
"""

from datetime import date
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
import subprocess

def test_january_with_dual_constraint():
    print("=" * 80)
    print("FINAL TEST: January 2026 with Dual-Constraint System")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  - 3 Teams × 5 Employees = 15 total")
    print("  - 48h/week target")
    print("  - January 2026: 31 days (Thu Jan 1 - Sat Jan 31)")
    print("  - Extended to complete weeks: Mon Dec 29, 2025 - Sun Feb 1, 2026 (35 days)")
    print("  - HARD CONSTRAINT: >= 192h minimum")
    print("  - SOFT CONSTRAINT: Target 213h (48÷7 × 31)")
    print("  - Max staffing: 10 per shift")
    print("  - Strict F→N→S team rotation")
    print()

    # Test with January 2026
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday

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
    
    # Update max staffing to 10
    cursor.execute("UPDATE ShiftTypes SET MaxStaffWeekday = 10, MaxStaffWeekend = 10")
    conn.commit()
    
    # Verify
    cursor.execute("SELECT Code, MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend FROM ShiftTypes")
    print("\nShift Staffing Configuration:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: weekday min={row[1]}, weekday max={row[2]}, weekend min={row[3]}, weekend max={row[4]}")
    
    conn.close()
    print("\n✓ Test data created: 3 teams with 5 employees each\n")

    # Load data
    print("Loading data from database...")
    employees, teams, absences, shift_types = load_from_database("dienstplan.db")
    global_settings = load_global_settings("dienstplan.db")
    
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len(employees)}")
    print(f"  Shift Types: {len(shift_types)}")
    print()

    # Create model
    print(f"Creating shift planning model for {start_date} to {end_date}...")
    print("This may take 2-3 minutes...")
    print()
    
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )

    print("Model statistics:")
    planning_model.print_model_statistics()
    print()

    # Solve
    print("Attempting to solve...")
    result = solve_shift_planning(planning_model, time_limit_seconds=180, global_settings=global_settings)

    print()
    print("=" * 80)
    if result:
        assignments, special_functions, complete_schedule = result
        print("RESULT: SUCCESS (FEASIBLE)")
    else:
        print("RESULT: INFEASIBLE")
    print("=" * 80)
    print()

    if result:
        print("✅ SUCCESS! Monthly shift planning is now FEASIBLE!")
        print()
        print("Solution Details:")
        
        # Analyze employee hours
        from collections import defaultdict
        employee_hours = defaultdict(int)
        employee_days = defaultdict(int)
        
        for assignment in assignments:
            employee_hours[assignment.employee_id] += 8
            employee_days[assignment.employee_id] += 1
        
        print()
        print("Employee Hours Distribution:")
        print("  Employee | Days | Hours | Status")
        print("  ---------|------|-------|-------")
        
        for emp in sorted(employees, key=lambda e: e.id):
            hours = employee_hours[emp.id]
            days = employee_days[emp.id]
            status_str = '✓ OK' if hours >= 192 else '✗ UNDER'
            if hours >= 213:
                status_str = '✓✓ TARGET+'
            elif hours >= 200:
                status_str = '✓+ GOOD'
            print(f"  {emp.vorname:<8} | {days:4} | {hours:5}h | {status_str}")
        
        print()
        avg_hours = sum(employee_hours.values()) / len(employees)
        min_hours = min(employee_hours.values())
        max_hours = max(employee_hours.values())
        
        print(f"  Average: {avg_hours:.1f}h per employee")
        print(f"  Minimum: {min_hours}h")
        print(f"  Maximum: {max_hours}h")
        print(f"  Target: 213h (soft)")
        print(f"  Hard min: 192h")
        print()
        
        # Check constraints
        under_min = [emp for emp in employees if employee_hours[emp.id] < 192]
        if under_min:
            print(f"⚠️  WARNING: {len(under_min)} employees under 192h minimum!")
            for emp in under_min:
                print(f"    - {emp.vorname}: {employee_hours[emp.id]}h")
        else:
            print("✅ All employees meet 192h hard minimum!")
        
        at_target = [emp for emp in employees if employee_hours[emp.id] >= 213]
        print(f"✓  {len(at_target)}/{len(employees)} employees at or above 213h target")
        print()
        
        return True
        
    else:
        print("✗ INFEASIBLE - Monthly planning still not working")
        print()
        print("This should NOT happen with the dual-constraint system.")
        print("The hard minimum (192h) should be achievable.")
        print()
        return False

if __name__ == "__main__":
    success = test_january_with_dual_constraint()
    print("=" * 80)
    if success:
        print("✅ TEST PASSED: Dual-constraint system successfully enables monthly planning")
    else:
        print("✗ TEST FAILED: Monthly planning still infeasible")
    print("=" * 80)
