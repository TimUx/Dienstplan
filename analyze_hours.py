"""
Analyze the solution from test_infeasible_issue.py to see actual hours worked.
"""

from datetime import date, timedelta
from entities import Employee, Team, STANDARD_SHIFT_TYPES, get_shift_type_by_id
from model import create_shift_planning_model
from solver import solve_shift_planning


def analyze_solution():
    """Analyze how many hours employees work without minimum hours constraint."""
    
    # Create same test data as test_infeasible_issue.py
    teams = [
        Team(id=1, name="Team 1", description="First team"),
        Team(id=2, name="Team 2", description="Second team"),
        Team(id=3, name="Team 3", description="Third team"),
    ]
    
    employees = []
    emp_id = 1
    for team_idx in range(3):
        team_id = team_idx + 1
        for member_idx in range(5):
            emp = Employee(
                id=emp_id,
                vorname=f"Employee{emp_id}",
                name=f"TeamMember{member_idx+1}",
                personalnummer=f"{team_id}{member_idx+1:02d}",
                team_id=team_id
            )
            employees.append(emp)
            emp_id += 1
    
    admin = Employee(
        id=emp_id,
        vorname="Admin",
        name="User",
        personalnummer="9999",
        team_id=None
    )
    employees.append(admin)
    
    start_date = date(2024, 1, 1)
    end_date = start_date + timedelta(days=30)  # 31 days
    absences = []
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees,
        teams,
        start_date,
        end_date,
        absences,
        shift_types=STANDARD_SHIFT_TYPES
    )
    
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("No solution found!")
        return
    
    assignments, special_functions, complete_schedule = result
    
    # Analyze hours per employee
    emp_hours = {}
    emp_days = {}
    
    for assignment in assignments:
        emp_id = assignment.employee_id
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        
        if emp_id not in emp_hours:
            emp_hours[emp_id] = 0
            emp_days[emp_id] = 0
        
        emp_hours[emp_id] += shift_type.hours
        emp_days[emp_id] += 1
    
    # Calculate weeks
    num_days = (end_date - start_date).days + 1
    num_weeks = num_days / 7.0
    
    print(f"\nAnalysis of solution (31 days = {num_weeks:.1f} weeks)")
    print("=" * 80)
    print(f"Weekly hours expectation from ShiftType: 40h")
    print(f"Expected monthly hours: 40h × {num_weeks:.1f} weeks = {40 * num_weeks:.1f}h")
    print()
    
    # Group by team
    for team in teams:
        team_emps = [e for e in employees if e.team_id == team.id]
        print(f"\n{team.name} ({len(team_emps)} employees):")
        print("-" * 80)
        
        for emp in team_emps:
            if emp.id in emp_hours:
                hours = emp_hours[emp.id]
                days = emp_days[emp.id]
                avg_weekly = hours / num_weeks
                shortfall = (40 * num_weeks) - hours
                
                status = "✓" if shortfall <= 0 else "✗"
                print(f"  {status} {emp.vorname:12s}: {hours:5.1f}h ({days:2d} days, "
                      f"avg {avg_weekly:.1f}h/week, shortfall: {shortfall:.1f}h)")
            else:
                print(f"  ✗ {emp.vorname:12s}: 0.0h (0 days, NOT WORKING)")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    employees_meeting_target = sum(1 for emp in employees if emp.team_id and emp.id in emp_hours and emp_hours[emp.id] >= 40 * num_weeks)
    employees_below_target = sum(1 for emp in employees if emp.team_id and (emp.id not in emp_hours or emp_hours[emp.id] < 40 * num_weeks))
    print(f"  Employees meeting target ({40 * num_weeks:.1f}h): {employees_meeting_target}")
    print(f"  Employees below target: {employees_below_target}")


if __name__ == "__main__":
    analyze_solution()
