"""
Debug script to understand the week structure and why warnings aren't printed.
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel

# Create minimal setup
shift_types = [
    ShiftType(id=1, code='F', name='Früh', start_time='06:00', end_time='14:30', 
             hours=8.5, min_staff_weekday=4, max_staff_weekday=6),
    ShiftType(id=2, code='S', name='Spät', start_time='13:30', end_time='22:00',
             hours=8.5, min_staff_weekday=3, max_staff_weekday=5),
    ShiftType(id=3, code='N', name='Nacht', start_time='21:30', end_time='06:30',
             hours=9, min_staff_weekday=3, max_staff_weekday=4),
]

teams = [Team(id=1, name='Alpha', allowed_shift_type_ids=[1, 2, 3])]

employees = []
for i in range(5):
    emp_id = i + 1
    emp = Employee(
        id=emp_id,
        vorname=f'First{emp_id}',
        name=f'Last{emp_id}',
        personalnummer=f'{emp_id:04d}',
        team_id=1,
    )
    employees.append(emp)

# Planning period: March 1-31, 2026
start_date = date(2026, 3, 1)  # Sunday
end_date = date(2026, 3, 31)    # Tuesday
absences = []

# Create conflicting locked assignments
locked_team_shift = {(1, 0): 'F'}
locked_employee_shift = {}
for day_offset in range(5):
    d = date(2026, 2, 23) + timedelta(days=day_offset)
    locked_employee_shift[(2, d)] = 'S'

print("Creating model...")
model = ShiftPlanningModel(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    shift_types=shift_types,
    locked_team_shift=locked_team_shift,
    locked_employee_shift=locked_employee_shift
)

print("\nModel Details:")
print(f"  Original start date: {model.original_start_date}")
print(f"  Original end date: {model.original_end_date}")
print(f"  Extended start date: {model.start_date}")
print(f"  Extended end date: {model.end_date}")
print(f"\n  Number of weeks: {len(model.weeks)}")

print("\nWeek structure:")
for idx, week_dates in enumerate(model.weeks):
    week_start = week_dates[0]
    week_end = week_dates[-1]
    
    # Check if boundary week
    week_spans_boundary = any(
        wd < model.original_start_date or wd > model.original_end_date 
        for wd in week_dates
    )
    
    boundary_marker = " [BOUNDARY WEEK]" if week_spans_boundary else ""
    print(f"  Week {idx}: {week_start} to {week_end}{boundary_marker}")
    
    # Check if our test dates are in this week
    test_date = date(2026, 2, 23)
    if test_date in week_dates:
        print(f"    -> Contains test date {test_date}")
        
print("\nEmployee shift locks:")
for (emp_id, d), shift_code in locked_employee_shift.items():
    # Check conditions
    outside_period = d < model.original_start_date or d > model.original_end_date
    
    # Find week
    week_idx_for_date = None
    date_in_boundary_week = False
    for idx, week_dates in enumerate(model.weeks):
        if d in week_dates:
            week_idx_for_date = idx
            week_spans_boundary = any(
                wd < model.original_start_date or wd > model.original_end_date 
                for wd in week_dates
            )
            date_in_boundary_week = week_spans_boundary
            break
    
    print(f"  Employee {emp_id}, Date {d}, Shift {shift_code}:")
    print(f"    - Outside original period: {outside_period}")
    print(f"    - Week index: {week_idx_for_date}")
    print(f"    - In boundary week: {date_in_boundary_week}")
    
    if outside_period:
        print(f"    ⚠️  SKIPPED: Date outside original planning period")
    elif date_in_boundary_week:
        print(f"    ⚠️  SKIPPED: Date in boundary week (spans month)")
    else:
        print(f"    ✓ Should be processed")
