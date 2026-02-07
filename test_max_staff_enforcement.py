"""
Test for enforcing max_staff constraints properly.

Problem: The N (night) shift has max 3 employees configured but is being
scheduled with 5 employees on many days, even though F (max 8) and S (max 6)
shifts have available capacity.

This test reproduces the issue and validates the fix.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_max_staff_not_exceeded_when_other_shifts_have_capacity():
    """
    Test that max staff limits are respected when other shifts have capacity.
    
    Scenario:
    - N shift: max 3 employees per day
    - S shift: max 6 employees per day  
    - F shift: max 8 employees per day
    - 15 employees total across 3 teams (5 per team)
    - When scheduling, N shift should NEVER exceed 3 employees if F or S have capacity
    
    Expected behavior:
    - On weekdays, no shift should exceed its maximum
    - If employees need hours, they should be distributed to F and S first
    - N shift should only get up to 3 employees max
    """
    print("=" * 70)
    print("TEST: Max Staff Enforcement When Other Shifts Have Capacity")
    print("=" * 70)
    
    # Create shift types matching the problem statement
    shift_types = [
        ShiftType(
            id=1, code='F', name='Früh', 
            start_time='05:45', end_time='13:45', 
            hours=8.0, 
            weekly_working_hours=48.0,  # 6 days * 8 hours
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
                name=f'Last{emp_id}',
                personalnummer=f'PN{emp_id:03d}',
                team_id=team_id,
            )
            employees.append(emp)
    
    # Planning period: February 2026 (28 days)
    start_date = date(2026, 2, 1)  # Sunday
    end_date = date(2026, 2, 28)    # Saturday
    absences = []
    
    print(f"\nSetup:")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  Teams: {len(teams)} teams")
    print(f"  Employees: {len(employees)} employees ({len(employees)//len(teams)} per team)")
    print(f"  Shift types:")
    for st in shift_types:
        print(f"    - {st.code} ({st.name}): max {st.max_staff_weekday} weekday, max {st.max_staff_weekend} weekend")
    
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
        shift_assignments, complete_schedule = solver.extract_solution()
        
        from collections import defaultdict
        
        # Count employees per shift per day
        shifts_by_date = defaultdict(lambda: defaultdict(int))
        
        for assignment in shift_assignments:
            d = assignment.date
            shift_type_id = assignment.shift_type_id
            
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
            
            # Count this assignment
            shifts_by_date[d][shift_code] += 1
        
        # Check for violations
        violations = []
        for d in sorted(shifts_by_date.keys()):
            is_weekend = d.weekday() >= 5
            day_name = d.strftime("%a %d")
            
            for shift_code in ['F', 'S', 'N']:
                count = shifts_by_date[d].get(shift_code, 0)
                
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
            
            # Focus on N shift violations
            n_violations = [v for v in violations if v['shift'] == 'N']
            if n_violations:
                print(f"\n⚠️  N SHIFT VIOLATIONS: {len(n_violations)} days")
                print("  This is the primary issue - N shift should never exceed 3 employees!")
                
                # Check if other shifts had capacity
                for v in n_violations:
                    d = v['date']
                    f_count = shifts_by_date[d].get('F', 0)
                    s_count = shifts_by_date[d].get('S', 0)
                    print(f"  {v['day']}: N={v['count']} (max 3), F={f_count} (max 8), S={s_count} (max 6)")
                    if f_count < 8 or s_count < 6:
                        print(f"    ↳ F or S had available capacity!")
        else:
            print("\n✓ NO VIOLATIONS: All shifts respect max staff limits")
        
        # Assert no violations
        assert len(violations) == 0, f"Max staff constraints violated on {len(violations)} days"
        
        # Special check for N shift
        n_violations = [v for v in violations if v['shift'] == 'N']
        assert len(n_violations) == 0, f"N shift exceeded max of 3 on {len(n_violations)} days"
        
        print("\n" + "=" * 70)
        print("TEST PASSED: Max staff constraints properly enforced")
        print("=" * 70)
        
    else:
        print(f"\n✗ No solution found!")
        print(f"  Status: {solver.status}")
        raise AssertionError("Solver failed to find a solution")


if __name__ == "__main__":
    test_max_staff_not_exceeded_when_other_shifts_have_capacity()
