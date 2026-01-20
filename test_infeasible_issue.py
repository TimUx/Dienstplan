"""
Test to reproduce the INFEASIBLE solver issue reported by the user.

User configuration:
- 3 teams with 5 employees each = 15 employees
- 1 admin user without a team = 1 employee
- Total: 16 employees
- 3 shifts: F (Früh), S (Spät), N (Nacht)
- All teams assigned to all three shifts
- Planning period: 31 days (about 1 month)
- Shift requirements: F=4 min, S=3 min, N=3 min
"""

from datetime import date, timedelta
from entities import Employee, Team, Absence, STANDARD_SHIFT_TYPES
from model import create_shift_planning_model
from solver import solve_shift_planning


def test_user_configuration():
    """
    Test the exact user configuration that causes INFEASIBLE.
    """
    # Create 3 teams
    teams = [
        Team(id=1, name="Team 1", description="First team"),
        Team(id=2, name="Team 2", description="Second team"),
        Team(id=3, name="Team 3", description="Third team"),
    ]
    
    # Create employees: 3 teams × 5 members = 15 employees
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
    
    # Add 1 admin user without a team
    admin = Employee(
        id=emp_id,
        vorname="Admin",
        name="User",
        personalnummer="9999",
        team_id=None  # No team
    )
    employees.append(admin)
    
    print(f"Total employees: {len(employees)}")
    print(f"Employees in teams: {len([e for e in employees if e.team_id])}")
    print(f"Employees without team: {len([e for e in employees if not e.team_id])}")
    
    # Planning period: 31 days
    start_date = date(2024, 1, 1)  # Start on a Monday
    end_date = start_date + timedelta(days=30)  # 31 days total
    
    print(f"Planning period: {start_date} to {end_date} ({(end_date - start_date).days + 1} days)")
    
    # No absences for this test
    absences = []
    
    # Create model
    print("\nCreating model...")
    planning_model = create_shift_planning_model(
        employees,
        teams,
        start_date,
        end_date,
        absences,
        shift_types=STANDARD_SHIFT_TYPES
    )
    
    planning_model.print_model_statistics()
    
    # Solve
    print("\nAttempting to solve...")
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\n✓ Solution found!")
        print(f"  - Total assignments: {len(assignments)}")
        print(f"  - TD assignments: {len(special_functions)}")
    else:
        print(f"\n✗ No solution found (INFEASIBLE)!")
        return False
    
    return True


if __name__ == "__main__":
    success = test_user_configuration()
    exit(0 if success else 1)
