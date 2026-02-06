"""
Test based on the actual problem statement showing N shift max violations.

The problem shows that on many days, 5 employees were assigned to N shift
when the maximum should be 3, even though F (max 8) and S (max 6) shifts
had available capacity.

This test reproduces that scenario with realistic data.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_february_2026_n_shift_overflow():
    """
    Reproduce the February 2026 scenario from the problem statement.
    
    The problem shows:
    - February 1-28, 2026 (28 days)
    - 15 employees in 3 teams (Alpha, Beta, Gamma)
    - N shift: max 3 employees
    - S shift: max 6 employees
    - F shift: max 8 employees
    - Weekly working hours: 48h (6 days * 8 hours)
    
    On weekdays Feb 9-13 (Mon-Fri), the problem shows that N shift had
    5 employees assigned on several days when max should be 3.
    """
    print("=" * 70)
    print("TEST: February 2026 N Shift Overflow Scenario")
    print("=" * 70)
    
    # Create shift types matching the problem statement
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='05:45', end_time='13:45', 
            hours=8.0, 
            weekly_working_hours=48.0,  # 6 days * 8 hours = target to reach
            min_staff_weekday=4, max_staff_weekday=8,
            min_staff_weekend=2, max_staff_weekend=8
        ),
        ShiftType(
            id=2, code='S', name='Spät', 
            start_time='13:45', end_time='21:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=6,
            min_staff_weekend=2, max_staff_weekend=6
        ),
        ShiftType(
            id=3, code='N', name='Nacht', 
            start_time='21:45', end_time='05:45',
            hours=8.0, 
            weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=3,  # MAX 3 for N shift!
            min_staff_weekend=2, max_staff_weekend=3
        ),
    ]
    
    # Create 3 teams matching the problem statement
    teams = [
        Team(id=1, name='Alpha', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=2, name='Beta', allowed_shift_type_ids=[1, 2, 3]),
        Team(id=3, name='Gamma', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create 15 employees (5 per team) matching the problem
    employees = []
    employee_names = [
        # Team Alpha (5 employees)
        ('Max', 'Müller', 'PN001', 1),
        ('Anna', 'Schmidt', 'PN002', 1),
        ('Peter', 'Weber', 'PN003', 1),
        ('Lisa', 'Meyer', 'PN004', 1),
        ('Robert', 'Franke', 'S001', 1),
        # Team Beta (5 employees)
        ('Julia', 'Becker', 'PN006', 2),
        ('Michael', 'Schulz', 'PN007', 2),
        ('Sarah', 'Hoffmann', 'PN008', 2),
        ('Daniel', 'Koch', 'PN009', 2),
        ('Thomas', 'Zimmermann', 'S002', 2),
        # Team Gamma (5 employees)
        ('Markus', 'Richter', 'PN011', 3),
        ('Stefanie', 'Klein', 'PN012', 3),
        ('Andreas', 'Wolf', 'PN013', 3),
        ('Nicole', 'Schröder', 'PN014', 3),
        ('Maria', 'Lange', 'S003', 3),
    ]
    
    for idx, (first, last, pn, team_id) in enumerate(employee_names, start=1):
        emp = Employee(
            id=idx,
            vorname=first,
            name=last,
            personalnummer=pn,
            team_id=team_id,
        )
        employees.append(emp)
    
    # Planning period: February 2026 (28 days)
    start_date = date(2026, 2, 1)  # Sunday, Feb 1
    end_date = date(2026, 2, 28)    # Saturday, Feb 28
    
    # Add some absences to make it more realistic and create pressure
    # Let's add a few days of absence for some employees
    from entities import AbsenceType
    absences = [
        # Employee 1 (PN001) absent Feb 11 (Wednesday)
        Absence(id=1, employee_id=1, absence_type=AbsenceType.U, 
                start_date=date(2026, 2, 11), end_date=date(2026, 2, 11)),
        # Employee 6 (PN006) absent Feb 5 (Thursday)  
        Absence(id=2, employee_id=6, absence_type=AbsenceType.U,
                start_date=date(2026, 2, 5), end_date=date(2026, 2, 5)),
        # Employee 11 (PN011) absent Feb 18 (Wednesday)
        Absence(id=3, employee_id=11, absence_type=AbsenceType.U,
                start_date=date(2026, 2, 18), end_date=date(2026, 2, 18)),
    ]
    
    print(f"\nSetup:")
    print(f"  Planning period: {start_date} to {end_date} (28 days)")
    print(f"  Teams: {len(teams)} teams")
    print(f"  Employees: {len(employees)} employees ({len(employees)//len(teams)} per team)")
    print(f"  Absences: {len(absences)} absence periods")
    print(f"  Shift types:")
    for st in shift_types:
        print(f"    - {st.code} ({st.name}): max {st.max_staff_weekday} weekday, weekly target {st.weekly_working_hours}h")
    print(f"\n  Expected behavior:")
    print(f"    - N shift should NEVER exceed 3 employees on any day")
    print(f"    - When employees need hours, they should fill F and S first")
    print(f"    - Only use N shift up to its maximum of 3")
    
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
    
    # Solve with longer timeout to ensure we find best solution
    print("Solving (300 second timeout)...")
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=300,
        num_workers=8
    )
    
    success = solver.solve()
    
    if success:
        print("\n✓ Solution found!")
        print(f"  Status: {solver.status}")
        
        # Extract schedule and check max staff constraints
        print("\nValidating max staff constraints...")
        
        # Get actual shift assignments
        shift_assignments, special_functions, complete_schedule = solver.extract_solution()
        
        from collections import defaultdict
        
        # Count employees per shift per day
        shifts_by_date = defaultdict(lambda: defaultdict(list))  # Store employee IDs
        
        for assignment in shift_assignments:
            d = assignment.date
            shift_type_id = assignment.shift_type_id
            emp_id = assignment.employee_id
            
            # Find shift code for this shift type ID
            shift_code = None
            for st in shift_types:
                if st.id == shift_type_id:
                    shift_code = st.code
                    break
            
            if not shift_code:
                continue
                
            # Skip absences
            if shift_code in ['U', 'AU', 'L', '+']:
                continue
            
            # Track this assignment
            shifts_by_date[d][shift_code].append(emp_id)
        
        # Check for violations
        violations = []
        for d in sorted(shifts_by_date.keys()):
            is_weekend = d.weekday() >= 5
            day_name = d.strftime("%a %d")
            
            for shift_code in ['F', 'S', 'N']:
                employee_ids = shifts_by_date[d].get(shift_code, [])
                count = len(employee_ids)
                
                # Find max staff for this shift
                max_staff = None
                for st in shift_types:
                    if st.code == shift_code:
                        max_staff = st.max_staff_weekend if is_weekend else st.max_staff_weekday
                        break
                
                if max_staff and count > max_staff:
                    violations.append({
                        'date': d,
                        'day': day_name,
                        'shift': shift_code,
                        'employee_ids': employee_ids,
                        'count': count,
                        'max': max_staff,
                        'excess': count - max_staff
                    })
        
        # Report findings
        if violations:
            print(f"\n❌ VIOLATIONS FOUND: {len(violations)} days with exceeded max staff")
            print("\nDetails:")
            for v in violations:
                print(f"  {v['day']}: {v['shift']} shift has {v['count']} employees (max {v['max']}, excess {v['excess']})")
                print(f"    Employee IDs: {v['employee_ids']}")
            
            # Focus on N shift violations
            n_violations = [v for v in violations if v['shift'] == 'N']
            if n_violations:
                print(f"\n⚠️  N SHIFT VIOLATIONS: {len(n_violations)} days")
                print("  This is the PRIMARY ISSUE - N shift should never exceed 3 employees!")
                
                # Check if other shifts had capacity
                print("\n  Checking if F or S shifts had available capacity:")
                for v in n_violations:
                    d = v['date']
                    f_count = len(shifts_by_date[d].get('F', []))
                    s_count = len(shifts_by_date[d].get('S', []))
                    print(f"  {v['day']}: N={v['count']} (max 3), F={f_count} (max 8), S={s_count} (max 6)")
                    if f_count < 8 or s_count < 6:
                        print(f"    ↳ PROBLEM: F or S had available capacity but N was overbooked!")
            
            # Assert no violations
            raise AssertionError(f"Max staff constraints violated on {len(violations)} days. "
                               f"N shift violations: {len(n_violations)}")
        else:
            print("\n✓ NO VIOLATIONS: All shifts respect max staff limits")
            
            # Print sample days to show proper distribution
            print("\nSample weekday distribution (first week Mon-Fri):")
            for day_num in range(2, 7):  # Feb 2-6 (Mon-Fri of first full week)
                d = date(2026, 2, day_num)
                if d in shifts_by_date:
                    f_count = len(shifts_by_date[d].get('F', []))
                    s_count = len(shifts_by_date[d].get('S', []))
                    n_count = len(shifts_by_date[d].get('N', []))
                    print(f"  {d.strftime('%a %d')}: F={f_count}, S={s_count}, N={n_count}")
        
        print("\n" + "=" * 70)
        print("TEST PASSED: Max staff constraints properly enforced")
        print("=" * 70)
        
    else:
        print(f"\n✗ No solution found!")
        print(f"  Status: {solver.status}")
        raise AssertionError("Solver failed to find a solution")


if __name__ == "__main__":
    test_february_2026_n_shift_overflow()
