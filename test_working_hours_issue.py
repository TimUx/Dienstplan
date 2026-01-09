"""
Test to reproduce the working hours issue described in the problem statement.

Problem: Employees assigned to teams with shifts (F, S, N) set to 48h/week 
should work 192h/month, but currently only work ~152h/month.
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import get_shift_type_by_id, STANDARD_SHIFT_TYPES

def test_current_working_hours():
    """Test current working hours to identify the issue"""
    print("\n" + "=" * 80)
    print("TEST: Current Working Hours Analysis")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Use 4 weeks for testing (1 month)
    start = date(2025, 1, 6)  # Monday
    end = start + timedelta(days=27)  # 4 weeks (28 days)
    
    print(f"\nPlanning period: {start} to {end} (4 weeks)")
    print(f"Shift types configuration:")
    for st in STANDARD_SHIFT_TYPES[:3]:  # F, S, N
        print(f"  {st.code} ({st.name}): {st.hours}h/day, {st.weekly_working_hours}h/week target")
    
    # Create and solve model
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("\n❌ FAIL: No solution found")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print(f"\n✓ Solution found with {len(assignments)} shift assignments")
    
    # Analyze working hours per employee
    print("\n" + "-" * 80)
    print("WORKING HOURS ANALYSIS (4 weeks)")
    print("-" * 80)
    
    emp_hours = {}
    emp_days = {}
    emp_weekly_hours = {}
    
    for assignment in assignments:
        emp_id = assignment.employee_id
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        
        if emp_id not in emp_hours:
            emp_hours[emp_id] = 0
            emp_days[emp_id] = []
            emp_weekly_hours[emp_id] = {}
        
        emp_hours[emp_id] += shift_type.hours
        emp_days[emp_id].append(assignment.date)
        
        # Track weekly hours
        week_num = (assignment.date - start).days // 7
        if week_num not in emp_weekly_hours[emp_id]:
            emp_weekly_hours[emp_id][week_num] = 0
        emp_weekly_hours[emp_id][week_num] += shift_type.hours
    
    # Print results for each employee
    for emp in employees:
        if emp.id not in emp_hours:
            continue
        
        total_hours = emp_hours[emp.id]
        days_worked = len(emp_days[emp.id])
        avg_weekly = total_hours / 4  # 4 weeks
        
        # Get employee's team
        team = next((t for t in teams if t.id == emp.team_id), None)
        team_name = team.name if team else "No team"
        
        print(f"\n{emp.full_name} ({team_name}):")
        print(f"  Total hours: {total_hours}h / 4 weeks")
        print(f"  Days worked: {days_worked}")
        print(f"  Average: {avg_weekly:.1f}h/week")
        
        # Show weekly breakdown
        print(f"  Weekly breakdown:")
        for week_num in sorted(emp_weekly_hours[emp.id].keys()):
            hours = emp_weekly_hours[emp.id][week_num]
            print(f"    Week {week_num + 1}: {hours}h")
        
        # Check if it meets expected 48h/week = 192h/month
        if total_hours < 192:
            shortfall = 192 - total_hours
            print(f"  ⚠️  SHORTFALL: {shortfall}h below expected 192h/month (48h/week)")
        else:
            print(f"  ✓ Meets target of 192h/month")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    employees_with_shortfall = 0
    total_shortfall = 0
    
    for emp in employees:
        if emp.id not in emp_hours:
            continue
        total_hours = emp_hours[emp.id]
        if total_hours < 192:
            shortfall = 192 - total_hours
            employees_with_shortfall += 1
            total_shortfall += shortfall
    
    print(f"Employees with shortfall: {employees_with_shortfall}/{len([e for e in employees if e.id in emp_hours])}")
    if employees_with_shortfall > 0:
        avg_shortfall = total_shortfall / employees_with_shortfall
        print(f"Average shortfall: {avg_shortfall:.1f}h/employee")
        print(f"Total shortfall: {total_shortfall:.1f}h")
        print("\n❌ ISSUE CONFIRMED: Employees are not reaching 48h/week (192h/month)")
    else:
        print("✓ All employees meet 192h/month target")
    
    return True

if __name__ == "__main__":
    test_current_working_hours()
