#!/usr/bin/env python3
"""
DEMONSTRATION: Fix for February 2026 Planning Failure

This script demonstrates that the fix resolves the issue described in the problem statement:
1. Successfully plan January 2026
2. Successfully plan February 2026 (which previously failed with INFEASIBLE)
3. Show that both plans work correctly with locked shifts from previous months

Run this script to verify the fix works for the user's exact scenario.
"""

import sys
from datetime import date
from data_loader import load_from_database
from model import create_shift_planning_model
from solver import solve_shift_planning

def print_header(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")

def main():
    print_header("DEMONSTRATION: February 2026 Planning Fix")
    
    print("This demonstration shows that the fix resolves the issue where:")
    print("✓ January 2026 planning works (user confirmed)")
    print("✗ February 2026 planning fails with INFEASIBLE (the bug)")
    print("✓ After fix: February 2026 works correctly")
    print()
    
    # Load real data from database
    try:
        employees, teams, absences, shift_types = load_from_database('dienstplan.db')
        print(f"Loaded {len(employees)} employees, {len(teams)} teams, {len(shift_types)} shift types")
    except Exception as e:
        print(f"⚠️  Could not load database: {e}")
        print("Creating minimal test data instead...")
        from entities import Employee, Team
        
        teams = [
            Team(id=1, name='Team Alpha', is_virtual=False),
            Team(id=2, name='Team Beta', is_virtual=False),
            Team(id=3, name='Team Gamma', is_virtual=False)
        ]
        
        employees = []
        for team_idx, team in enumerate(teams, 1):
            for emp_idx in range(5):  # 5 employees per team
                emp_id = (team_idx - 1) * 5 + emp_idx + 1
                emp = Employee(
                    id=emp_id,
                    name=f'Employee {emp_id}',
                    team_id=team.id,
                    allowed_shift_codes=['F', 'N', 'S'],
                    monthly_hours_target=240
                )
                employees.append(emp)
                team.employees.append(emp)
        
        absences = []
        shift_types = None
    
    print()
    
    # ==========================================================================
    # STEP 1: Plan January 2026
    # ==========================================================================
    print_header("STEP 1: Planning January 2026")
    
    jan_start = date(2026, 1, 1)
    jan_end = date(2026, 1, 31)
    
    print(f"Planning period: {jan_start} to {jan_end}")
    print("Creating planning model...")
    
    jan_model = create_shift_planning_model(
        employees, teams, jan_start, jan_end, absences,
        shift_types=shift_types
    )
    
    print(f"  Original period: {jan_model.original_start_date} to {jan_model.original_end_date}")
    print(f"  Extended period: {jan_model.start_date} to {jan_model.end_date}")
    print(f"  Extended days: {(jan_model.end_date - jan_model.start_date).days + 1}")
    print()
    
    print("Solving (30 second time limit)...")
    jan_result = solve_shift_planning(jan_model, time_limit_seconds=30)
    
    if jan_result:
        print("✓ January 2026: PLANNING SUCCESSFUL")
        print(f"  Total assignments: {len(jan_result)}")
    else:
        print("✗ January 2026: PLANNING FAILED")
        print("  This is unexpected - January should work")
        return 1
    
    # Extract locked shifts from January that fall into February's planning window
    print()
    print("Extracting locked shifts from January for February planning...")
    
    feb_start = date(2026, 2, 1)
    feb_end = date(2026, 2, 28)
    
    # Calculate February's extended period
    from datetime import timedelta
    feb_extended_start = feb_start
    if feb_start.weekday() != 0:  # Not Monday
        feb_extended_start = feb_start - timedelta(days=feb_start.weekday())
    
    feb_extended_end = feb_end
    if feb_end.weekday() != 6:  # Not Sunday
        feb_extended_end = feb_end + timedelta(days=6 - feb_end.weekday())
    
    print(f"  February extended period: {feb_extended_start} to {feb_extended_end}")
    
    # Find January assignments that fall into February's extended period
    locked_employee_shift = {}
    for assignment in jan_result:
        if feb_extended_start <= assignment.date <= feb_extended_end:
            shift_code = next((st.code for st in shift_types if st.id == assignment.shift_type_id), 
                             ['F', 'N', 'S'][assignment.shift_type_id % 3] if shift_types is None else None)
            if shift_code:
                locked_employee_shift[(assignment.employee_id, assignment.date)] = shift_code
    
    print(f"  Found {len(locked_employee_shift)} locked assignments from January")
    
    # Show some examples
    if locked_employee_shift:
        print("  Examples of locked shifts:")
        for (emp_id, d), shift in list(locked_employee_shift.items())[:5]:
            print(f"    Employee {emp_id}, {d} → {shift}")
    
    # ==========================================================================
    # STEP 2: Plan February 2026 (WITH LOCKED SHIFTS FROM JANUARY)
    # ==========================================================================
    print_header("STEP 2: Planning February 2026 with Locked Shifts")
    
    print(f"Planning period: {feb_start} to {feb_end}")
    print(f"Extended period: {feb_extended_start} to {feb_extended_end}")
    print(f"Locked shifts from January: {len(locked_employee_shift)}")
    print()
    
    print("Creating planning model with locked shifts...")
    
    feb_model = create_shift_planning_model(
        employees, teams, feb_start, feb_end, absences,
        shift_types=shift_types,
        locked_employee_shift=locked_employee_shift
    )
    
    print(f"  Model created with {len(feb_model.locked_team_shift)} team locks")
    print(f"  (Team locks only for dates within Feb 1-28, not for Jan 26-31)")
    print()
    
    print("Solving (30 second time limit)...")
    feb_result = solve_shift_planning(feb_model, time_limit_seconds=30)
    
    if feb_result:
        print("✓ February 2026: PLANNING SUCCESSFUL")
        print(f"  Total assignments: {len(feb_result)}")
        print()
        print("✓✓✓ FIX VERIFIED - February planning works with locked shifts! ✓✓✓")
    else:
        print("✗ February 2026: PLANNING FAILED")
        print("  The fix may not be working correctly")
        return 1
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print_header("SUMMARY")
    
    print("Results:")
    print("  ✓ January 2026 planned successfully")
    print("  ✓ February 2026 planned successfully with locked shifts from January")
    print()
    print("The fix successfully resolves the INFEASIBLE error by:")
    print("  1. Loading employee-level locks from adjacent months (prevents double shifts)")
    print("  2. NOT converting them to team-level locks (prevents conflicts)")
    print("  3. Only creating team-level locks for dates within the target month")
    print()
    print("This allows sequential month planning without conflicts!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
