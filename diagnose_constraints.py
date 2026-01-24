#!/usr/bin/env python3
"""
Diagnostic tool to identify which constraints are causing infeasibility.
Tests different constraint combinations to isolate the root cause.
"""

from datetime import date
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import ShiftPlanningSolver
from ortools.sat.python import cp_model
from constraints import (
    add_team_shift_assignment_constraints,
    add_team_rotation_constraints,
    add_employee_team_linkage_constraints,
    add_staffing_constraints,
    add_rest_time_constraints,
    add_consecutive_shifts_constraints,
    add_working_hours_constraints,
    add_weekly_block_constraints,
    add_team_member_block_constraints
)
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

def test_constraint_combination(test_name, start_date, end_date, constraint_flags):
    """
    Test a specific combination of constraints
    
    constraint_flags: dict with keys:
        - enable_team_rotation: bool
        - enable_min_hours: bool
        - enable_max_consecutive: bool
        - enable_block_scheduling: bool
        - enable_rest_time: bool
    """
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Constraints enabled: {constraint_flags}")
    print()

    employees, teams, absences, shift_types = load_from_database("dienstplan.db")
    global_settings = load_global_settings("dienstplan.db")

    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )

    # Create solver with custom constraint flags
    solver = ShiftPlanningSolver(planning_model)
    
    # Modify solver to skip certain constraints (we'll do this manually)
    model = cp_model.CpModel()
    
    # Create variables
    team_shift = {}
    employee_active = {}
    employee_weekend_shift = {}
    employee_cross_team_shift = {}
    employee_cross_team_weekend = {}
    td_vars = {}
    
    dates = planning_model.dates
    weeks = planning_model.weeks
    shift_codes = planning_model.shift_codes
    
    # Team shift variables (always needed)
    for team in teams:
        for week_idx in range(len(weeks)):
            for shift_code in shift_codes:
                team_shift[(team.id, week_idx, shift_code)] = model.NewBoolVar(
                    f'team_{team.id}_week_{week_idx}_shift_{shift_code}'
                )
    
    # Employee active variables
    for emp in employees:
        if emp.team_id:
            for d in dates:
                if d.weekday() < 5:  # Weekdays
                    employee_active[(emp.id, d)] = model.NewBoolVar(f'emp_{emp.id}_active_{d}')
                else:  # Weekends
                    employee_weekend_shift[(emp.id, d)] = model.NewBoolVar(f'emp_{emp.id}_weekend_{d}')
    
    # Cross-team variables
    for emp in employees:
        for d in dates:
            for shift_code in shift_codes:
                if d.weekday() < 5:
                    employee_cross_team_shift[(emp.id, d, shift_code)] = model.NewBoolVar(
                        f'emp_{emp.id}_cross_{d}_{shift_code}'
                    )
                else:
                    employee_cross_team_weekend[(emp.id, d, shift_code)] = model.NewBoolVar(
                        f'emp_{emp.id}_cross_weekend_{d}_{shift_code}'
                    )
    
    print("Adding constraints:")
    
    # 1. Team shift assignment (always required)
    print("  [ALWAYS] Team shift assignment")
    add_team_shift_assignment_constraints(model, team_shift, teams, weeks, shift_codes)
    
    # 2. Team rotation
    if constraint_flags.get('enable_team_rotation', True):
        print("  [ENABLED] Team rotation (F → N → S)")
        add_team_rotation_constraints(model, team_shift, teams, weeks, shift_codes)
    else:
        print("  [DISABLED] Team rotation")
    
    # 3. Employee-team linkage (always required)
    print("  [ALWAYS] Employee-team linkage")
    add_employee_team_linkage_constraints(model, employee_active, employee_weekend_shift, team_shift,
                              employees, teams, dates, weeks, shift_codes, absences)
    
    # 4. Staffing requirements (always required)
    print("  [ALWAYS] Staffing requirements")
    add_staffing_constraints(model, employee_active, employee_weekend_shift, 
                             employee_cross_team_shift, employee_cross_team_weekend,
                             employees, dates, shift_types, absences)
    
    # 5. Rest time constraints
    if constraint_flags.get('enable_rest_time', True):
        print("  [ENABLED] Rest time constraints")
        add_rest_time_constraints(model, employee_cross_team_shift, employee_cross_team_weekend,
                                 employees, dates, weeks, shift_types, absences)
    else:
        print("  [DISABLED] Rest time constraints")
    
    # 6. Consecutive shifts
    if constraint_flags.get('enable_max_consecutive', True):
        print("  [ENABLED] Max consecutive shifts")
        add_consecutive_shifts_constraints(model, team_shift, teams, weeks, shift_codes, shift_types)
    else:
        print("  [DISABLED] Max consecutive shifts")
    
    # 7. Working hours constraints
    if constraint_flags.get('enable_min_hours', True):
        print("  [ENABLED] Minimum working hours")
        add_working_hours_constraints(model, employee_active, employee_weekend_shift,
                                     employee_cross_team_shift, employee_cross_team_weekend,
                                     employees, dates, weeks, shift_types, absences)
    else:
        print("  [DISABLED] Minimum working hours")
    
    # 8. Block scheduling
    if constraint_flags.get('enable_block_scheduling', True):
        print("  [ENABLED] Block scheduling (soft)")
        add_weekly_block_constraints(model, employee_active, employee_cross_team_shift,
                                    employees, dates, weeks, shift_codes, absences)
        block_vars = add_team_member_block_constraints(model, employee_active, employee_weekend_shift,
                                                       team_shift, employees, teams, dates, weeks,
                                                       shift_codes, absences)
    else:
        print("  [DISABLED] Block scheduling")
        block_vars = []
    
    # Set objective (just minimize if we have block vars)
    if block_vars:
        model.Minimize(sum([-v for v in block_vars]))
    
    print("\nSolving...")
    solver_obj = cp_model.CpSolver()
    solver_obj.parameters.max_time_in_seconds = 60
    solver_obj.parameters.log_search_progress = False
    solver_obj.parameters.num_search_workers = 8
    
    status = solver_obj.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"✓ FEASIBLE (status: {'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'})")
        print(f"  Solve time: {solver_obj.WallTime():.2f}s")
        return True
    else:
        print(f"✗ INFEASIBLE (status: {solver_obj.StatusName(status)})")
        return False

def main():
    """Run diagnostic tests"""
    if not setup_test_data():
        return
    
    # Test period
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    print("\n" + "="*80)
    print("CONSTRAINT DIAGNOSIS FOR JANUARY 2026")
    print("="*80)
    
    results = {}
    
    # Test 1: Minimal constraints (baseline)
    results['baseline'] = test_constraint_combination(
        "Baseline (minimal constraints)",
        start_date, end_date,
        {
            'enable_team_rotation': False,
            'enable_min_hours': False,
            'enable_max_consecutive': False,
            'enable_block_scheduling': False,
            'enable_rest_time': False,
        }
    )
    
    # Test 2: Add team rotation
    results['with_rotation'] = test_constraint_combination(
        "With team rotation",
        start_date, end_date,
        {
            'enable_team_rotation': True,
            'enable_min_hours': False,
            'enable_max_consecutive': False,
            'enable_block_scheduling': False,
            'enable_rest_time': False,
        }
    )
    
    # Test 3: Add minimum hours
    results['with_min_hours'] = test_constraint_combination(
        "With team rotation + minimum hours",
        start_date, end_date,
        {
            'enable_team_rotation': True,
            'enable_min_hours': True,
            'enable_max_consecutive': False,
            'enable_block_scheduling': False,
            'enable_rest_time': False,
        }
    )
    
    # Test 4: Add max consecutive
    results['with_consecutive'] = test_constraint_combination(
        "With team rotation + minimum hours + max consecutive",
        start_date, end_date,
        {
            'enable_team_rotation': True,
            'enable_min_hours': True,
            'enable_max_consecutive': True,
            'enable_block_scheduling': False,
            'enable_rest_time': False,
        }
    )
    
    # Test 5: Add block scheduling
    results['with_blocks'] = test_constraint_combination(
        "With team rotation + minimum hours + max consecutive + block scheduling",
        start_date, end_date,
        {
            'enable_team_rotation': True,
            'enable_min_hours': True,
            'enable_max_consecutive': True,
            'enable_block_scheduling': True,
            'enable_rest_time': False,
        }
    )
    
    # Test 6: All constraints
    results['all_constraints'] = test_constraint_combination(
        "All constraints enabled",
        start_date, end_date,
        {
            'enable_team_rotation': True,
            'enable_min_hours': True,
            'enable_max_consecutive': True,
            'enable_block_scheduling': True,
            'enable_rest_time': True,
        }
    )
    
    # Summary
    print("\n" + "="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)
    for test_name, feasible in results.items():
        status = "✓ FEASIBLE" if feasible else "✗ INFEASIBLE"
        print(f"{test_name:.<50} {status}")
    
    print("\n" + "="*80)
    print("CONCLUSIONS:")
    print("="*80)
    
    # Find the breaking point
    if results['baseline'] and not results['with_rotation']:
        print("❌ Team rotation constraint causes infeasibility")
    elif results['with_rotation'] and not results['with_min_hours']:
        print("❌ Minimum hours constraint (combined with rotation) causes infeasibility")
    elif results['with_min_hours'] and not results['with_consecutive']:
        print("❌ Max consecutive shifts constraint causes infeasibility")
    elif results['with_consecutive'] and not results['with_blocks']:
        print("❌ Block scheduling constraints cause infeasibility")
    elif results['with_blocks'] and not results['all_constraints']:
        print("❌ Rest time constraints cause infeasibility")
    else:
        print("⚠️  Complex interaction between multiple constraints")
    
    print("\nKey observations:")
    print("- 3 teams with 5 members each = 15 employees")
    print("- 31 days in January, ~5 weeks")
    print("- Min staffing: F=4, S=3, N=3 per day")
    print("- Target: 192h/month = 24 days per employee")
    print("- Team rotation: F → N → S (changes weekly)")

if __name__ == "__main__":
    main()
