"""
Analysis of shift planning requirements for January 2026.

This script analyzes the mathematical feasibility of creating a shift plan
for 3 teams with 5 members each, working F, S, N shifts at 48h/week.
"""

from datetime import date, timedelta
from calendar import monthrange
from entities import ShiftType, Employee, Team, STANDARD_SHIFT_TYPES
from typing import List, Dict

def get_january_2026_dates() -> List[date]:
    """Get all dates in January 2026."""
    year = 2026
    month = 1
    _, num_days = monthrange(year, month)
    return [date(year, month, day) for day in range(1, num_days + 1)]

def count_weekdays_weekends(dates: List[date]) -> Dict[str, int]:
    """Count weekdays (Mon-Fri) and weekend days (Sat-Sun)."""
    weekdays = sum(1 for d in dates if d.weekday() < 5)
    weekends = len(dates) - weekdays
    return {
        'weekdays': weekdays,
        'weekend_days': weekends,
        'total_days': len(dates)
    }

def calculate_hours_requirements(weekly_hours: float, num_days: int, shift_hours: float) -> Dict[str, float]:
    """Calculate monthly hours requirements and days needed."""
    num_weeks = num_days / 7.0
    monthly_hours = weekly_hours * num_weeks
    days_needed = monthly_hours / shift_hours
    return {
        'num_weeks': num_weeks,
        'monthly_hours': monthly_hours,
        'days_needed': days_needed
    }

def analyze_staffing_capacity(dates: List[date], shift_types: List[ShiftType], 
                              num_employees: int, days_needed: float) -> Dict:
    """Analyze if staffing capacity meets requirements."""
    day_counts = count_weekdays_weekends(dates)
    
    # Get staffing requirements from first shift type (F, S, N all have same values)
    shift = shift_types[0]
    min_weekday = shift.min_staff_weekday
    max_weekday = shift.max_staff_weekday
    min_weekend = shift.min_staff_weekend
    max_weekend = shift.max_staff_weekend
    
    # Calculate total slots available
    weekday_slots_min = day_counts['weekdays'] * min_weekday
    weekday_slots_max = day_counts['weekdays'] * max_weekday
    weekend_slots_min = day_counts['weekend_days'] * min_weekend
    weekend_slots_max = day_counts['weekend_days'] * max_weekend
    
    total_slots_min = weekday_slots_min + weekend_slots_min
    total_slots_max = weekday_slots_max + weekend_slots_max
    
    # Calculate total employee-days needed
    total_employee_days = num_employees * days_needed
    
    return {
        'weekday_slots_min': weekday_slots_min,
        'weekday_slots_max': weekday_slots_max,
        'weekend_slots_min': weekend_slots_min,
        'weekend_slots_max': weekend_slots_max,
        'total_slots_min': total_slots_min,
        'total_slots_max': total_slots_max,
        'total_employee_days': total_employee_days,
        'feasible_min': total_employee_days <= total_slots_max,
        'staffing': {
            'min_weekday': min_weekday,
            'max_weekday': max_weekday,
            'min_weekend': min_weekend,
            'max_weekend': max_weekend
        }
    }

def calculate_optimal_staffing(num_employees: int, days_needed: float, 
                               weekdays: int, weekend_days: int) -> Dict:
    """Calculate optimal staffing levels to meet employee hour targets."""
    total_employee_days = num_employees * days_needed
    
    # If we can fit everything in weekdays
    if days_needed <= weekdays:
        max_staff_weekday_needed = num_employees  # All can work on same day if needed
        max_staff_weekend_needed = 0
    else:
        # Need weekend work
        weekend_days_per_employee = days_needed - weekdays
        total_weekend_days_needed = num_employees * weekend_days_per_employee
        max_staff_weekend_needed = int(total_weekend_days_needed / weekend_days) + 1
        max_staff_weekday_needed = num_employees
    
    # Calculate average staff per day
    avg_staff_per_day = total_employee_days / (weekdays + weekend_days)
    
    return {
        'total_employee_days': total_employee_days,
        'max_staff_weekday_needed': max_staff_weekday_needed,
        'max_staff_weekend_needed': max_staff_weekend_needed,
        'avg_staff_per_day': avg_staff_per_day
    }

def main():
    """Run the analysis for January 2026."""
    print("=" * 80)
    print("SHIFT PLANNING ANALYSIS FOR JANUARY 2026")
    print("=" * 80)
    
    # Configuration
    num_teams = 3
    num_employees_per_team = 5
    num_employees = num_teams * num_employees_per_team
    
    # Get F, S, N shifts (48h/week configured)
    shift_types_fsn = [st for st in STANDARD_SHIFT_TYPES if st.code in ['F', 'S', 'N']]
    weekly_hours = shift_types_fsn[0].weekly_working_hours  # All have same value
    shift_hours = shift_types_fsn[0].hours
    
    # Get January 2026 dates
    dates = get_january_2026_dates()
    day_counts = count_weekdays_weekends(dates)
    
    print(f"\n1. CONFIGURATION")
    print(f"   Teams: {num_teams}")
    print(f"   Employees per team: {num_employees_per_team}")
    print(f"   Total employees: {num_employees}")
    print(f"   Shift types: F (Früh), S (Spät), N (Nacht)")
    print(f"   Weekly working hours: {weekly_hours}h")
    print(f"   Shift duration: {shift_hours}h")
    
    print(f"\n2. JANUARY 2026 CALENDAR")
    print(f"   Total days: {day_counts['total_days']}")
    print(f"   Weekdays (Mon-Fri): {day_counts['weekdays']}")
    print(f"   Weekend days (Sat-Sun): {day_counts['weekend_days']}")
    
    # First day of January 2026
    first_day = dates[0]
    print(f"   First day: {first_day.strftime('%A, %B %d, %Y')}")
    
    # Calculate hours requirements
    hours_req = calculate_hours_requirements(weekly_hours, day_counts['total_days'], shift_hours)
    
    print(f"\n3. HOURS REQUIREMENTS PER EMPLOYEE")
    print(f"   Number of weeks: {hours_req['num_weeks']:.2f}")
    print(f"   Target monthly hours: {hours_req['monthly_hours']:.1f}h")
    print(f"   Days needed to reach target: {hours_req['days_needed']:.1f} days")
    print(f"   Hours per day: {shift_hours}h")
    
    print(f"\n4. CALCULATION: DAYS NEEDED")
    print(f"   Formula: (weekly_hours × num_weeks) / shift_hours")
    print(f"   = ({weekly_hours}h × {hours_req['num_weeks']:.2f}) / {shift_hours}h")
    print(f"   = {hours_req['monthly_hours']:.1f}h / {shift_hours}h")
    print(f"   = {hours_req['days_needed']:.1f} days")
    
    # Analyze current staffing capacity
    capacity = analyze_staffing_capacity(dates, shift_types_fsn, num_employees, hours_req['days_needed'])
    
    print(f"\n5. CURRENT STAFFING CONSTRAINTS (from STANDARD_SHIFT_TYPES)")
    print(f"   Weekdays: min={capacity['staffing']['min_weekday']}, max={capacity['staffing']['max_weekday']}")
    print(f"   Weekends: min={capacity['staffing']['min_weekend']}, max={capacity['staffing']['max_weekend']}")
    
    print(f"\n6. CAPACITY ANALYSIS")
    print(f"   Total employee-days needed: {capacity['total_employee_days']:.1f}")
    print(f"   Weekday slots: {capacity['weekday_slots_min']} to {capacity['weekday_slots_max']}")
    print(f"   Weekend slots: {capacity['weekend_slots_min']} to {capacity['weekend_slots_max']}")
    print(f"   Total slots available: {capacity['total_slots_min']} to {capacity['total_slots_max']}")
    
    if capacity['feasible_min']:
        print(f"   ✓ FEASIBLE: Total slots ({capacity['total_slots_max']}) >= employee-days ({capacity['total_employee_days']:.1f})")
    else:
        print(f"   ✗ INFEASIBLE: Total slots ({capacity['total_slots_max']}) < employee-days ({capacity['total_employee_days']:.1f})")
        deficit = capacity['total_employee_days'] - capacity['total_slots_max']
        print(f"   Deficit: {deficit:.1f} employee-days")
    
    # Calculate optimal staffing
    optimal = calculate_optimal_staffing(num_employees, hours_req['days_needed'], 
                                        day_counts['weekdays'], day_counts['weekend_days'])
    
    print(f"\n7. OPTIMAL STAFFING REQUIREMENTS")
    print(f"   To meet {hours_req['monthly_hours']:.1f}h/employee target:")
    print(f"   Maximum staff needed on weekdays: {optimal['max_staff_weekday_needed']}")
    print(f"   Maximum staff needed on weekends: {optimal['max_staff_weekend_needed']}")
    print(f"   Average staff per day: {optimal['avg_staff_per_day']:.1f}")
    
    # Team rotation constraints
    print(f"\n8. TEAM ROTATION CONSTRAINTS")
    print(f"   System uses F → N → S rotation pattern")
    print(f"   Each team works ONE shift per week")
    print(f"   All {num_employees_per_team} members of a team work the SAME shift that week")
    print(f"   With {num_teams} teams and 3 shifts (F, N, S):")
    print(f"   - Week 1: Team 1=F, Team 2=N, Team 3=S")
    print(f"   - Week 2: Team 1=N, Team 2=S, Team 3=F")
    print(f"   - Week 3: Team 1=S, Team 2=F, Team 3=N")
    print(f"   - Week 4: Team 1=F, Team 2=N, Team 3=S (cycle repeats)")
    
    print(f"\n9. IMPACT OF TEAM ROTATION ON CAPACITY")
    print(f"   When a team is assigned to a shift, all {num_employees_per_team} members work that shift")
    print(f"   If max_staff_weekday = {capacity['staffing']['max_weekday']}, and team size = {num_employees_per_team}:")
    if num_employees_per_team <= capacity['staffing']['max_weekday']:
        print(f"   ✓ All team members CAN work (team size ≤ max staff)")
    else:
        print(f"   ✗ Team is TOO LARGE for max staff constraint")
    
    # Detailed day-by-day analysis
    print(f"\n10. DAY-BY-DAY WORK DISTRIBUTION")
    if hours_req['days_needed'] <= day_counts['weekdays']:
        print(f"   Employee needs {hours_req['days_needed']:.1f} days")
        print(f"   Available weekdays: {day_counts['weekdays']}")
        print(f"   ✓ Can be satisfied with weekdays only")
        weekend_days_needed = 0
    else:
        weekend_days_needed = hours_req['days_needed'] - day_counts['weekdays']
        print(f"   Employee needs {hours_req['days_needed']:.1f} days")
        print(f"   Available weekdays: {day_counts['weekdays']}")
        print(f"   Additional weekend days needed: {weekend_days_needed:.1f}")
        print(f"   Available weekend days: {day_counts['weekend_days']}")
        if weekend_days_needed <= day_counts['weekend_days']:
            print(f"   ✓ Enough weekend days available")
        else:
            print(f"   ✗ Not enough weekend days!")
    
    # Analysis conclusion
    print(f"\n11. INFEASIBILITY ANALYSIS")
    print(f"   Current configuration shows: {'FEASIBLE' if capacity['feasible_min'] else 'INFEASIBLE'}")
    
    if not capacity['feasible_min']:
        print(f"\n   WHY INFEASIBLE?")
        print(f"   - Each employee needs {hours_req['days_needed']:.1f} days of work")
        print(f"   - Total: {num_employees} × {hours_req['days_needed']:.1f} = {capacity['total_employee_days']:.1f} employee-days")
        print(f"   - Maximum slots: {capacity['total_slots_max']}")
        print(f"   - Shortfall: {capacity['total_employee_days'] - capacity['total_slots_max']:.1f} employee-days")
        
        print(f"\n   SOLUTIONS:")
        print(f"   Option 1: Increase max_staff limits")
        new_max_weekday = int(capacity['total_employee_days'] / day_counts['weekdays']) + 1
        print(f"      Set max_staff_weekday ≥ {new_max_weekday}")
        
        print(f"   Option 2: Reduce weekly hours target")
        max_weekly_hours = (capacity['total_slots_max'] * shift_hours) / (num_employees * hours_req['num_weeks'])
        print(f"      Set weekly_working_hours ≤ {max_weekly_hours:.1f}h")
        
        print(f"   Option 3: Reduce team size or number of employees")
        max_employees = int(capacity['total_slots_max'] / hours_req['days_needed'])
        print(f"      Maximum employees with current constraints: {max_employees}")
    else:
        print(f"\n   Current configuration is mathematically FEASIBLE.")
        print(f"   If solver returns INFEASIBLE, check:")
        print(f"   1. Team rotation constraints (F → N → S pattern)")
        print(f"   2. Rest time constraints (11h between shifts)")
        print(f"   3. Consecutive work days (max 6 days)")
        print(f"   4. Weekend fairness constraints")
        print(f"   5. Cross-team assignment restrictions")
    
    print(f"\n" + "=" * 80)
    print(f"SUMMARY")
    print(f"=" * 80)
    print(f"Monthly target: {hours_req['monthly_hours']:.1f}h per employee")
    print(f"Days required: {hours_req['days_needed']:.1f} days per employee")
    print(f"Current max staffing: weekday={capacity['staffing']['max_weekday']}, weekend={capacity['staffing']['max_weekend']}")
    print(f"Recommended max staffing: weekday={optimal['max_staff_weekday_needed']}, weekend={optimal['max_staff_weekend_needed']}")
    print(f"Result: {'FEASIBLE ✓' if capacity['feasible_min'] else 'INFEASIBLE ✗'}")
    print(f"=" * 80)

if __name__ == "__main__":
    main()
