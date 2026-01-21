"""
Test shift planning for January 2026 with 3 teams of 5 employees.
Reproduce the INFEASIBLE issue and diagnose the root cause.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, STANDARD_SHIFT_TYPES
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
from typing import List

def create_january_2026_test_data():
    """Create test data for January 2026 with 3 teams of 5 employees each."""
    
    # Get F, S, N shift types (48h/week)
    shift_types = [st for st in STANDARD_SHIFT_TYPES if st.code in ['F', 'S', 'N']]
    
    # Create 3 teams
    teams = [
        Team(id=1, name="Team Alpha", description="First shift team"),
        Team(id=2, name="Team Beta", description="Second shift team"),
        Team(id=3, name="Team Gamma", description="Third shift team")
    ]
    
    # Create 15 employees (5 per team)
    employees = []
    emp_id = 1
    team_names = ["Alpha", "Beta", "Gamma"]
    
    for team_idx, team in enumerate(teams):
        for member_num in range(1, 6):
            employee = Employee(
                id=emp_id,
                vorname=f"Mitarbeiter_{team_names[team_idx]}",
                name=f"M{member_num}",
                personalnummer=f"{team_idx+1}{member_num:02d}",
                team_id=team.id
            )
            employees.append(employee)
            team.employees.append(employee)
            emp_id += 1
    
    # Set allowed shift types for each team (all can do F, S, N)
    for team in teams:
        team.allowed_shift_type_ids = [st.id for st in shift_types]
    
    # Generate January 2026 dates
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    return employees, teams, dates, shift_types, []  # No absences


def test_january_2026_basic():
    """Test basic shift planning for January 2026."""
    print("=" * 80)
    print("TEST: January 2026 Shift Planning - 3 Teams, 5 Members, 48h/week")
    print("=" * 80)
    
    # Create test data
    employees, teams, dates, shift_types, absences = create_january_2026_test_data()
    
    print(f"\nTest Configuration:")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees per team: {len(teams[0].employees)}")
    print(f"  Total employees: {len(employees)}")
    print(f"  Shift types: {', '.join([st.code for st in shift_types])}")
    print(f"  Planning period: {dates[0]} to {dates[-1]} ({len(dates)} days)")
    print(f"  Weekly hours: {shift_types[0].weekly_working_hours}h")
    
    # Calculate requirements
    num_weeks = len(dates) / 7.0
    monthly_hours = shift_types[0].weekly_working_hours * num_weeks
    days_needed = monthly_hours / shift_types[0].hours
    
    print(f"\nHours Requirements:")
    print(f"  Weeks: {num_weeks:.2f}")
    print(f"  Target monthly hours: {monthly_hours:.1f}h")
    print(f"  Days needed per employee: {days_needed:.1f}")
    
    # Create and solve model
    try:
        print(f"\nCreating shift planning model...")
        model = ShiftPlanningModel(employees, teams, dates, shift_types, absences)
        
        print(f"Creating solver...")
        solver = ShiftPlanningSolver(model, time_limit_seconds=60, num_workers=4)
        
        print(f"Adding constraints...")
        solver.add_all_constraints()
        
        print(f"Running solver...")
        result = solver.solve()
        
        print(f"\n" + "=" * 80)
        print(f"SOLVER RESULT")
        print(f"=" * 80)
        print(f"Status: {result['status']}")
        
        if result['status'] == 'OPTIMAL' or result['status'] == 'FEASIBLE':
            print(f"✓ Solution found!")
            print(f"Objective value: {result.get('objective', 'N/A')}")
            
            # Analyze solution
            assignments = result.get('assignments', [])
            print(f"\nTotal assignments: {len(assignments)}")
            
            # Count days per employee
            employee_days = {}
            for assignment in assignments:
                emp_id = assignment.employee_id
                employee_days[emp_id] = employee_days.get(emp_id, 0) + 1
            
            print(f"\nDays worked per employee:")
            if shift_types:  # Guard against empty shift_types
                for emp in employees[:5]:  # Show first 5
                    days = employee_days.get(emp.id, 0)
                    hours = days * shift_types[0].hours
                    print(f"  {emp.full_name}: {days} days = {hours}h (target: {monthly_hours:.1f}h)")
            
        elif result['status'] == 'INFEASIBLE':
            print(f"✗ INFEASIBLE - No solution exists!")
            print(f"\nPossible reasons:")
            print(f"  1. Team rotation constraints too restrictive")
            print(f"  2. Staffing min/max conflict with team size")
            print(f"  3. Hours target unreachable with team rotation")
            print(f"  4. Rest time constraints conflict")
            print(f"  5. Consecutive work days limit too strict")
            
        else:
            print(f"? Unknown status: {result['status']}")
        
        print(f"\n" + "=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_january_2026_with_relaxed_constraints():
    """Test with relaxed staffing constraints."""
    print("\n\n" + "=" * 80)
    print("TEST: January 2026 with RELAXED Staffing Constraints")
    print("=" * 80)
    
    # Create test data
    employees, teams, dates, shift_types_orig, absences = create_january_2026_test_data()
    
    # Relax staffing constraints - increase max staff
    shift_types = []
    for st in shift_types_orig:
        st_relaxed = ShiftType(
            id=st.id,
            code=st.code,
            name=st.name,
            start_time=st.start_time,
            end_time=st.end_time,
            color_code=st.color_code,
            hours=st.hours,
            weekly_working_hours=st.weekly_working_hours,
            min_staff_weekday=1,  # Reduced minimum
            max_staff_weekday=15,  # Allow all 15 to work if needed
            min_staff_weekend=1,   # Reduced minimum
            max_staff_weekend=15,  # Allow all 15 to work if needed
            works_monday=st.works_monday,
            works_tuesday=st.works_tuesday,
            works_wednesday=st.works_wednesday,
            works_thursday=st.works_thursday,
            works_friday=st.works_friday,
            works_saturday=st.works_saturday,
            works_sunday=st.works_sunday
        )
        shift_types.append(st_relaxed)
    
    print(f"\nRelaxed Configuration:")
    print(f"  Min staff: 1 (weekday and weekend)")
    print(f"  Max staff: 15 (weekday and weekend)")
    
    # Create and solve model
    try:
        model = ShiftPlanningModel(employees, teams, dates, shift_types, absences)
        solver = ShiftPlanningSolver(model, time_limit_seconds=60, num_workers=4)
        solver.add_all_constraints()
        
        print(f"Running solver with relaxed constraints...")
        result = solver.solve()
        
        print(f"\n" + "=" * 80)
        print(f"SOLVER RESULT (Relaxed)")
        print(f"=" * 80)
        print(f"Status: {result['status']}")
        
        if result['status'] == 'OPTIMAL' or result['status'] == 'FEASIBLE':
            print(f"✓ Solution found with relaxed constraints!")
            print(f"\nThis suggests the original min/max staffing constraints were too restrictive.")
        elif result['status'] == 'INFEASIBLE':
            print(f"✗ Still INFEASIBLE even with relaxed constraints!")
            print(f"\nThis suggests the issue is with:")
            print(f"  - Team rotation pattern (F → N → S)")
            print(f"  - Working hours target (48h/week = 212.6h/month)")
            print(f"  - Or a fundamental constraint conflict")
        
        print(f"\n" + "=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run both tests
    result1 = test_january_2026_basic()
    result2 = test_january_2026_with_relaxed_constraints()
    
    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Standard constraints): {result1.get('status', 'ERROR') if result1 else 'ERROR'}")
    print(f"Test 2 (Relaxed constraints): {result2.get('status', 'ERROR') if result2 else 'ERROR'}")
    print("=" * 80)
