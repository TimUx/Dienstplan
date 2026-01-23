"""
Test script to reproduce the shift planning issue.
Creates 3 teams with 5 employees each and attempts planning.
"""

import sqlite3
from datetime import date, timedelta

def setup_test_data(db_path="dienstplan.db"):
    """Set up test data: 3 teams with 5 employees each"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete existing employees (except admin) and teams
    cursor.execute("DELETE FROM Employees WHERE Id > 1")
    cursor.execute("DELETE FROM Teams")
    
    # Create 3 teams
    teams = [
        ("Team Alpha", "First shift team", "team-alpha@test.com"),
        ("Team Beta", "Second shift team", "team-beta@test.com"),
        ("Team Gamma", "Third shift team", "team-gamma@test.com")
    ]
    
    for name, desc, email in teams:
        cursor.execute("""
            INSERT INTO Teams (Name, Description, Email, IsVirtual)
            VALUES (?, ?, ?, 0)
        """, (name, desc, email))
    
    # Get team IDs
    cursor.execute("SELECT Id, Name FROM Teams ORDER BY Id")
    team_ids = {row[1]: row[0] for row in cursor.fetchall()}
    
    # Create 5 employees per team (15 total)
    employees = [
        # Team Alpha
        ("Max", "Müller", "1001", "max.mueller@test.com", team_ids["Team Alpha"], 1, 0),
        ("Anna", "Schmidt", "1002", "anna.schmidt@test.com", team_ids["Team Alpha"], 0, 0),
        ("Peter", "Weber", "1003", "peter.weber@test.com", team_ids["Team Alpha"], 0, 0),
        ("Lisa", "Meyer", "1004", "lisa.meyer@test.com", team_ids["Team Alpha"], 0, 0),
        ("Tom", "Wagner", "1005", "tom.wagner@test.com", team_ids["Team Alpha"], 0, 0),
        # Team Beta
        ("Julia", "Becker", "2001", "julia.becker@test.com", team_ids["Team Beta"], 1, 0),
        ("Michael", "Schulz", "2002", "michael.schulz@test.com", team_ids["Team Beta"], 0, 0),
        ("Sarah", "Hoffmann", "2003", "sarah.hoffmann@test.com", team_ids["Team Beta"], 0, 0),
        ("Daniel", "Koch", "2004", "daniel.koch@test.com", team_ids["Team Beta"], 0, 0),
        ("Laura", "Bauer", "2005", "laura.bauer@test.com", team_ids["Team Beta"], 0, 0),
        # Team Gamma
        ("Markus", "Richter", "3001", "markus.richter@test.com", team_ids["Team Gamma"], 1, 0),
        ("Stefanie", "Klein", "3002", "stefanie.klein@test.com", team_ids["Team Gamma"], 0, 0),
        ("Andreas", "Wolf", "3003", "andreas.wolf@test.com", team_ids["Team Gamma"], 0, 0),
        ("Nicole", "Schröder", "3004", "nicole.schroeder@test.com", team_ids["Team Gamma"], 0, 0),
        ("Christian", "Neumann", "3005", "christian.neumann@test.com", team_ids["Team Gamma"], 0, 0),
    ]
    
    for vorname, name, persnr, email, team_id, td_qual, springer in employees:
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, TeamId, IsTdQualified, IsSpringer, IsActive)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (vorname, name, persnr, email, team_id, td_qual, springer))
    
    conn.commit()
    conn.close()
    print("✓ Test data created: 3 teams with 5 employees each")


def test_planning(db_path="dienstplan.db"):
    """Test shift planning"""
    from data_loader import load_from_database, load_global_settings
    from model import create_shift_planning_model
    from solver import solve_shift_planning
    
    print("\n" + "="*60)
    print("TESTING SHIFT PLANNING")
    print("="*60)
    
    # Test planning for next month
    today = date.today()
    # Get first day of next month
    if today.month == 12:
        start_date = date(today.year + 1, 1, 1)
    else:
        start_date = date(today.year, today.month + 1, 1)
    
    # Get last day of that month
    if start_date.month == 12:
        end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Days: {(end_date - start_date).days + 1}")
    
    # Load data
    print("\nLoading data from database...")
    employees, teams, absences, shift_types = load_from_database(db_path)
    print(f"  - Employees: {len(employees)}")
    print(f"  - Teams: {len(teams)}")
    print(f"  - Absences: {len(absences)}")
    print(f"  - Shift types: {len(shift_types)}")
    
    # Show team composition
    print("\nTeam composition:")
    for team in teams:
        members = [e for e in employees if e.team_id == team.id]
        print(f"  - {team.name}: {len(members)} members")
        for emp in members:
            td = "TD-qualified" if emp.is_td_qualified else ""
            print(f"    • {emp.vorname} {emp.name} {td}")
    
    # Show shift types
    print("\nShift types:")
    for st in shift_types:
        print(f"  - {st.code}: {st.name} ({st.start_time}-{st.end_time}, {st.weekly_working_hours}h/week)")
        print(f"    Min/Max weekday: {st.min_staff_weekday}/{st.max_staff_weekday}")
        print(f"    Min/Max weekend: {st.min_staff_weekend}/{st.max_staff_weekend}")
    
    # Load global settings
    global_settings = load_global_settings(db_path)
    print(f"\nGlobal settings:")
    print(f"  - Max consecutive shifts: {global_settings['max_consecutive_shifts_weeks']} weeks")
    print(f"  - Max consecutive night shifts: {global_settings['max_consecutive_night_shifts_weeks']} weeks")
    print(f"  - Min rest hours: {global_settings['min_rest_hours']} hours")
    
    # Create model
    print("\n" + "="*60)
    print("CREATING MODEL")
    print("="*60)
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )
    planning_model.print_model_statistics()
    
    # Solve
    print("\n" + "="*60)
    print("SOLVING")
    print("="*60)
    result = solve_shift_planning(planning_model, time_limit_seconds=300, global_settings=global_settings)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ SOLUTION FOUND!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
        print(f"  - Complete schedule entries: {len(complete_schedule)}")
        
        # Show sample assignments
        print("\nSample assignments (first 10):")
        for i, assignment in enumerate(assignments[:10]):
            emp = next((e for e in employees if e.id == assignment.employee_id), None)
            st = next((s for s in shift_types if s.id == assignment.shift_type_id), None)
            if emp and st:
                print(f"  {i+1}. {emp.vorname} {emp.name} -> {st.code} on {assignment.date}")
    else:
        print(f"\n✗ NO SOLUTION FOUND!")
        print("Check diagnostics above for details.")
        return False
    
    return True


if __name__ == "__main__":
    setup_test_data()
    success = test_planning()
    exit(0 if success else 1)
