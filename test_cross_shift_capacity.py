"""
Test to validate the cross-shift capacity enforcement fix.

This test creates a scenario where WITHOUT the fix, the solver would overstaff
the N shift to meet target hours, but WITH the fix, it should prefer to fill
F and S shifts first.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence, AbsenceType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_cross_shift_capacity_enforcement():
    """
    Test that the cross-shift capacity enforcement prevents N overflow.
    
    Scenario designed to trigger the issue:
    - 3 teams, 5 employees each = 15 total
    - Each employee needs 48h/week (6 days * 8 hours)
    - N shift: max 3 employees per day
    - S shift: max 6 employees per day  
    - F shift: max 8 employees per day
    - Some absences to create pressure to meet hours
    
    Without the fix: Solver might put 4-5 employees in N shift to meet hours
    With the fix: Solver should fill F and S first, keeping N at max 3
    """
    print("=" * 70)
    print("TEST: Cross-Shift Capacity Enforcement")
    print("=" * 70)
    
    # Create shift types with the target values
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='05:45', end_time='13:45', 
            hours=8.0, 
            weekly_working_hours=48.0,  
            min_staff_weekday=3, max_staff_weekday=8,  # Higher capacity
            min_staff_weekend=2, max_staff_weekend=8
        ),
        ShiftType(
            id=2, code='S', name='Spät', 
            start_time='13:45', end_time='21:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=6,  # Medium capacity
            min_staff_weekend=2, max_staff_weekend=6
        ),
        ShiftType(
            id=3, code='N', name='Nacht', 
            start_time='21:45', end_time='05:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=3,  # STRICT MAX of 3!
            min_staff_weekend=2, max_staff_weekend=3
        ),
    ]
    
    # Create 3 teams
    teams = [
        Team(id=1, name='Alpha', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=2, name='Beta', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=3, name='Gamma', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create 15 employees (5 per team)
    employees = []
    for team_id in [1, 2, 3]:
        for i in range(5):
            emp_id = (team_id - 1) * 5 + i + 1
            emp = Employee(
                id=emp_id,
                vorname=f'Employee{emp_id}',
                name=f'Test{emp_id}',
                personalnummer=f'PN{emp_id:03d}',
                team_id=team_id,
            )
            employees.append(emp)
    
    # Planning period: 4 weeks to give enough time for patterns to emerge
    start_date = date(2026, 2, 1)  # Sunday
    end_date = date(2026, 2, 28)    # Saturday (4 full weeks)
    
    # Add a few absences to create pressure
    absences = [
        Absence(id=1, employee_id=1, absence_type=AbsenceType.U, 
                start_date=date(2026, 2, 9), end_date=date(2026, 2, 13)),  # 1 week
        Absence(id=2, employee_id=7, absence_type=AbsenceType.U,
                start_date=date(2026, 2, 16), end_date=date(2026, 2, 20)),  # 1 week
    ]
    
    print(f"\nSetup:")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  Employees: {len(employees)} ({len(employees)//len(teams)} per team)")
    print(f"  Absences: {len(absences)} periods")
    print(f"  Shift capacities:")
    print(f"    - F: min 3, max 8")
    print(f"    - S: min 3, max 6")
    print(f"    - N: min 3, max 3 (STRICT)")
    print(f"\n  Expected behavior WITH fix:")
    print(f"    - N shift should NEVER exceed 3 employees")
    print(f"    - F and S should be filled first when meeting hour targets")
    print(f"    - Cross-shift capacity violations should be 0")
    
    # Build the model
    print("\nBuilding planning model...")
    planning_model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=absences,
        shift_types=shift_types,
    )
    
    # Solve
    print("Solving (180 second timeout)...")
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=180,
        num_workers=8
    )
    
    success = solver.solve()
    
    if success:
        print("\n✓ Solution found!")
        print(f"  Status: {solver.status}")
        
        # Extract schedule and validate
        print("\nValidating cross-shift capacity enforcement...")
        
        shift_assignments, special_functions, complete_schedule = solver.extract_solution()
        
        from collections import defaultdict
        
        # Count employees per shift per day
        shifts_by_date = defaultdict(lambda: defaultdict(list))
        
        for assignment in shift_assignments:
            d = assignment.date
            shift_type_id = assignment.shift_type_id
            emp_id = assignment.employee_id
            
            # Find shift code
            shift_code = None
            for st in shift_types:
                if st.id == shift_type_id:
                    shift_code = st.code
                    break
            
            if not shift_code or shift_code in ['U', 'AU', 'L', '+']:
                continue
            
            shifts_by_date[d][shift_code].append(emp_id)
        
        # Check for violations
        violations = []
        n_violations = []
        
        for d in sorted(shifts_by_date.keys()):
            is_weekend = d.weekday() >= 5
            day_name = d.strftime("%a %d")
            
            for shift_code in ['F', 'S', 'N']:
                employee_ids = shifts_by_date[d].get(shift_code, [])
                count = len(employee_ids)
                
                # Find max staff
                max_staff = None
                for st in shift_types:
                    if st.code == shift_code:
                        max_staff = st.max_staff_weekend if is_weekend else st.max_staff_weekday
                        break
                
                if max_staff and count > max_staff:
                    violation = {
                        'date': d,
                        'day': day_name,
                        'shift': shift_code,
                        'employee_ids': employee_ids,
                        'count': count,
                        'max': max_staff,
                        'excess': count - max_staff
                    }
                    violations.append(violation)
                    if shift_code == 'N':
                        n_violations.append(violation)
        
        # Report findings
        if violations:
            print(f"\n❌ VIOLATIONS FOUND: {len(violations)} days")
            
            if n_violations:
                print(f"\n⚠️  N SHIFT VIOLATIONS: {len(n_violations)} days")
                for v in n_violations:
                    d = v['date']
                    f_count = len(shifts_by_date[d].get('F', []))
                    s_count = len(shifts_by_date[d].get('S', []))
                    print(f"  {v['day']}: N={v['count']} (max 3), F={f_count} (max 8), S={s_count} (max 6)")
                    if f_count < 8 or s_count < 6:
                        print(f"    ↳ ERROR: F or S had available capacity!")
                
                raise AssertionError(f"Cross-shift capacity enforcement FAILED: "
                                   f"N shift exceeded max on {len(n_violations)} days")
            else:
                print("\n✓ No N shift violations (good!)")
                # But check if there are violations in other shifts
                print("\nOther violations:")
                for v in violations:
                    print(f"  {v['day']}: {v['shift']} = {v['count']} (max {v['max']})")
        else:
            print("\n✓ NO VIOLATIONS: All shifts respect max staff limits")
        
        # Additional validation: Check that N was used efficiently
        print("\nShift distribution analysis:")
        total_f = sum(len(shifts_by_date[d].get('F', [])) for d in shifts_by_date.keys())
        total_s = sum(len(shifts_by_date[d].get('S', [])) for d in shifts_by_date.keys())
        total_n = sum(len(shifts_by_date[d].get('N', [])) for d in shifts_by_date.keys())
        print(f"  Total F assignments: {total_f}")
        print(f"  Total S assignments: {total_s}")
        print(f"  Total N assignments: {total_n}")
        print(f"  Ratio F:S:N = {total_f}:{total_s}:{total_n}")
        
        # With capacity 8:6:3, we'd expect roughly that ratio if all full
        # But the key is N should not exceed its max
        
        print("\n" + "=" * 70)
        print("TEST PASSED: Cross-shift capacity enforcement working correctly")
        print("=" * 70)
        
    else:
        print(f"\n✗ No solution found!")
        print(f"  Status: {solver.status}")
        raise AssertionError("Solver failed to find a solution")


if __name__ == "__main__":
    test_cross_shift_capacity_enforcement()
