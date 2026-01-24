"""
Systematic Constraint Analysis for January 2026
Tests each constraint individually to identify the blocker preventing monthly planning
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from ortools.sat.python import cp_model
from solver import create_shift_planning_model
from db_setup import init_db, Session
from db_models import Employee, Team, ShiftType, Absence
import time

def test_with_constraints_disabled(constraint_name, disable_list):
    """Test planning with specific constraints disabled"""
    print(f"\n{'='*80}")
    print(f"TEST: {constraint_name}")
    print(f"Disabled: {', '.join(disable_list)}")
    print('='*80)
    
    # Initialize database
    init_db()
    session = Session()
    
    # Clean up
    session.query(Employee).delete()
    session.query(Team).delete()
    session.query(ShiftType).delete()
    session.query(Absence).delete()
    session.commit()
    
    # Create 3 teams
    teams = []
    for i in range(1, 4):
        team = Team(name=f"Team {i}")
        session.add(team)
        session.flush()
        teams.append(team)
    
    # Create 5 employees per team
    employees = []
    for team in teams:
        for j in range(1, 6):
            emp = Employee(
                vorname=f"Mitarbeiter{len(employees)+1}",
                nachname=f"Team{team.id}",
                personalnummer=f"MA{len(employees)+1:03d}",
                team_id=team.id,
                wochenstunden=48.0
            )
            session.add(emp)
            session.flush()
            employees.append(emp)
    
    # Create shift types
    shift_types = []
    for name, min_val, max_val in [("F", 4, 10), ("S", 3, 10), ("N", 3, 10)]:
        st = ShiftType(
            name=name,
            min_mitarbeiter=min_val,
            max_mitarbeiter=max_val,
            beginn="06:00",
            ende="14:00",
            dauer_stunden=8.0
        )
        session.add(st)
        session.flush()
        shift_types.append(st)
    
    session.commit()
    
    # Planning period: January 2026 extended to complete weeks
    start_date = date(2025, 12, 29)  # Monday before Jan 1
    end_date = date(2026, 2, 1)      # Sunday after Jan 31
    
    print(f"\nConfiguration:")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len(employees)} ({len(employees)//len(teams)} per team)")
    print(f"  Period: {start_date} to {end_date} ({(end_date - start_date).days} days)")
    print(f"  Shift Types: {[st.name for st in shift_types]}")
    print(f"  Min/Max: F={shift_types[0].min_mitarbeiter}/{shift_types[0].max_mitarbeiter}, "
          f"S={shift_types[1].min_mitarbeiter}/{shift_types[1].max_mitarbeiter}, "
          f"N={shift_types[2].min_mitarbeiter}/{shift_types[2].max_mitarbeiter}")
    
    # Create model with constraints disabled
    try:
        model, variables = create_shift_planning_model(
            session,
            start_date,
            end_date,
            disabled_constraints=disable_list
        )
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.log_search_progress = False
        
        start_time = time.time()
        status = solver.Solve(model)
        solve_time = time.time() - start_time
        
        status_name = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN"
        }.get(status, f"UNKNOWN({status})")
        
        print(f"\nResult: {status_name}")
        print(f"Solve Time: {solve_time:.2f}s")
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"✅ FEASIBLE - This constraint set works!")
            return True
        else:
            print(f"✗ INFEASIBLE - Still blocked")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False
    finally:
        session.close()

# Test progression
tests = [
    # Step 1: Baseline - NO constraints (should be FEASIBLE)
    ("Baseline: NO constraints", ["all"]),
    
    # Step 2: Add only basic staffing
    ("Only staffing constraints", ["team_rotation", "working_hours", "rest_time", "consecutive_shifts", "blocks", "fairness"]),
    
    # Step 3: Add team rotation
    ("Staffing + Team Rotation", ["working_hours", "rest_time", "consecutive_shifts", "blocks", "fairness"]),
    
    # Step 4: Add working hours (HARD 192h + SOFT proportional)
    ("Staffing + Rotation + Working Hours", ["rest_time", "consecutive_shifts", "blocks", "fairness"]),
    
    # Step 5: Add rest time (11 hours)
    ("Staffing + Rotation + Hours + Rest Time", ["consecutive_shifts", "blocks", "fairness"]),
    
    # Step 6: Add consecutive shifts limit
    ("Staffing + Rotation + Hours + Rest + Consecutive", ["blocks", "fairness"]),
    
    # Step 7: Add block preferences (soft)
    ("Staffing + Rotation + Hours + Rest + Consecutive + Blocks", ["fairness"]),
    
    # Step 8: Full constraints
    ("ALL constraints enabled", []),
]

print("\n" + "="*80)
print("SYSTEMATIC CONSTRAINT ANALYSIS")
print("Testing January 2026: 3 teams × 5 employees, 48h/week")
print("="*80)

results = []
for test_name, disabled in tests:
    result = test_with_constraints_disabled(test_name, disabled)
    results.append((test_name, result))
    
    # Stop if we found the blocker
    if not result and len(results) > 1 and results[-2][1]:
        print(f"\n{'='*80}")
        print(f"🔍 BLOCKER IDENTIFIED!")
        print(f"Last working: {results[-2][0]}")
        print(f"First failing: {test_name}")
        
        # Identify which constraint was added
        prev_disabled = tests[len(results)-2][1]
        curr_disabled = disabled
        added = [c for c in prev_disabled if c not in curr_disabled]
        print(f"Constraint causing INFEASIBLE: {', '.join(added) if added else 'UNKNOWN'}")
        print('='*80)

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print('='*80)
for test_name, result in results:
    status = "✅ FEASIBLE" if result else "✗ INFEASIBLE"
    print(f"{status}: {test_name}")

print("\nAnalysis complete.")
