#!/usr/bin/env python3
"""
Test January 2026 shift planning with DYNAMIC STAFFING.

Key insight from @TimUx:
- Minimum staffing (F=4, S=3, N=3) is the MINIMUM required, not maximum
- System should use MORE workers when needed to meet minimum hours requirement
- Each employee must work ~24 days (192h / 8h) in 31-day month
- With 15 employees needing 24 days each = 360 person-days total
- Must distribute 360 person-days across 31 days × 3 shifts = 93 shift-days
- Average: 360 / 93 ≈ 3.87 workers per shift-day
- But need to respect min staffing: F≥4, S≥3, N≥3

Solution: Use flexible staffing that can exceed minimums when needed.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from models import Team, Employee, ShiftType, Absence
from solver import solve_shift_planning
from db_init import create_default_shift_types

def test_january_2026_dynamic_staffing():
    """
    Test January 2026 (31 days, Thu Jan 1 - Sat Jan 31) with dynamic staffing.
    
    Parameters:
    - 3 teams with 5 employees each (15 total)
    - Weekly hours: 48h (6 days/week average)
    - Monthly hours: 192h minimum (24 days in 31-day month)
    - Shift staffing: Min as required, Max set high to allow flexibility
    """
    print("="*80)
    print("JANUARY 2026 SHIFT PLANNING TEST - DYNAMIC STAFFING")
    print("="*80)
    
    # Date range: January 2026 (extended to complete weeks)
    # Jan 1 is Thursday, Jan 31 is Saturday
    # Extended: Mon Dec 29, 2025 - Sun Feb 1, 2026 (5 complete weeks)
    start_date = date(2025, 12, 29)  # Monday before Jan 1
    end_date = date(2026, 2, 1)      # Sunday after Jan 31
    
    print(f"\nPlanning Period (5 complete weeks):")
    print(f"  Start: {start_date.strftime('%a %b %d, %Y')}")
    print(f"  End:   {end_date.strftime('%a %b %d, %Y')}")
    print(f"  Total days: {(end_date - start_date).days + 1}")
    print(f"  Weeks: 5 complete weeks (Mon-Sun)")
    
    # Create shift types with FLEXIBLE MAX STAFFING
    # Min values stay as required, Max set high to allow dynamic distribution
    shift_types = [
        ShiftType(
            id=1,
            name="Frühschicht",
            code="F",
            start_time="06:00",
            end_time="14:00",
            duration_hours=8.0,
            min_staff_weekday=4,    # Minimum required
            max_staff_weekday=15,   # Allow up to ALL employees if needed
            min_staff_weekend=4,
            max_staff_weekend=15,
            color="#FFD700",
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=2,
            name="Spätschicht", 
            code="S",
            start_time="14:00",
            end_time="22:00",
            duration_hours=8.0,
            min_staff_weekday=3,    # Minimum required
            max_staff_weekday=15,   # Allow up to ALL employees if needed
            min_staff_weekend=3,
            max_staff_weekend=15,
            color="#FF6B6B",
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=3,
            name="Nachtschicht",
            code="N",
            start_time="22:00",
            end_time="06:00",
            duration_hours=8.0,
            min_staff_weekday=3,    # Minimum required
            max_staff_weekday=15,   # Allow up to ALL employees if needed
            min_staff_weekend=3,
            max_staff_weekend=15,
            color="#4ECDC4",
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
    ]
    
    # Create 3 teams with 5 employees each
    teams = []
    employees = []
    
    for team_num in range(1, 4):
        team = Team(
            id=team_num,
            name=f"Team {team_num}",
            allowed_shift_type_ids=[1, 2, 3]  # All teams can work F, N, S
        )
        teams.append(team)
        
        for emp_num in range(1, 6):
            emp_id = (team_num - 1) * 5 + emp_num
            employee = Employee(
                id=emp_id,
                name=f"Employee {emp_id}",
                team_id=team.id,
                weekly_hours=48.0,  # 6 days/week
                is_weekend_worker=True
            )
            employees.append(employee)
    
    print(f"\nConfiguration:")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len(employees)} ({len(employees)//len(teams)} per team)")
    print(f"  Weekly hours per employee: 48h (6 days)")
    print(f"  Monthly hours target: 192h (24 days) MINIMUM")
    
    print(f"\nShift Staffing (DYNAMIC):")
    for st in shift_types:
        print(f"  {st.code}: min={st.min_staff_weekday}, max={st.max_staff_weekday} (flexible!)")
    
    # Calculate capacity
    total_days = (end_date - start_date).days + 1
    required_person_days = len(employees) * 24  # 24 days minimum per employee
    min_capacity = total_days * (4 + 3 + 3)  # Using minimum staffing
    max_capacity = total_days * (15 + 15 + 15)  # Using maximum staffing
    
    print(f"\nCapacity Analysis:")
    print(f"  Required: {len(employees)} employees × 24 days = {required_person_days} person-days")
    print(f"  Min capacity: {total_days} days × {4+3+3} min workers = {min_capacity} person-days")
    print(f"  Max capacity: {total_days} days × {15+15+15} max workers = {max_capacity} person-days")
    print(f"  Required fits in range: {min_capacity} ≤ {required_person_days} ≤ {max_capacity} ✓")
    
    # No absences
    absences = []
    
    print(f"\n{'='*80}")
    print("RUNNING SOLVER with dynamic staffing...")
    print(f"{'='*80}\n")
    
    # Solve
    result = solve_shift_planning(
        employees=employees,
        teams=teams,
        shift_types=shift_types,
        start_date=start_date,
        end_date=end_date,
        absences=absences,
        time_limit_seconds=300  # 5 minutes
    )
    
    print(f"\n{'='*80}")
    print(f"RESULT: {result['status']}")
    print(f"{'='*80}")
    
    if result["status"] == "OPTIMAL" or result["status"] == "FEASIBLE":
        print("\n✅ SUCCESS! Shift planning FEASIBLE with dynamic staffing!")
        
        assignments = result.get("assignments", [])
        print(f"\nTotal assignments: {len(assignments)}")
        
        # Count days worked per employee
        employee_days = {}
        for emp in employees:
            employee_days[emp.id] = set()
        
        for assignment in assignments:
            if assignment["date"] >= date(2026, 1, 1) and assignment["date"] <= date(2026, 1, 31):
                employee_days[assignment["employee_id"]].add(assignment["date"])
        
        # Display results
        print(f"\nEmployee Work Distribution (January 2026 only):")
        for emp in sorted(employees, key=lambda e: e.id):
            days_worked = len(employee_days[emp.id])
            hours = days_worked * 8
            print(f"  {emp.name:15s}: {days_worked:2d} days ({hours:3d}h) - Target: 24 days (192h)")
        
        # Check if all employees meet minimum
        all_meet_minimum = all(len(employee_days[emp.id]) >= 24 for emp in employees)
        print(f"\nAll employees meet 24-day minimum: {'✅ YES' if all_meet_minimum else '❌ NO'}")
        
        # Count workers per shift per day
        shift_staffing = {}
        for assignment in assignments:
            d = assignment["date"]
            shift = assignment["shift_code"]
            if (d, shift) not in shift_staffing:
                shift_staffing[(d, shift)] = 0
            shift_staffing[(d, shift)] += 1
        
        print(f"\nShift Staffing Summary:")
        for st in shift_types:
            counts = [shift_staffing.get((d, st.code), 0) 
                     for d in [start_date + timedelta(days=i) 
                              for i in range((end_date - start_date).days + 1)]]
            if counts:
                print(f"  {st.code}: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
        
        return True
    else:
        print(f"\n❌ FAILED: {result['status']}")
        if "error" in result:
            print(f"Error: {result['error']}")
        return False


if __name__ == "__main__":
    success = test_january_2026_dynamic_staffing()
    sys.exit(0 if success else 1)
