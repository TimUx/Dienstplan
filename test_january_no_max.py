#!/usr/bin/env python3
"""
Test shift planning for January 2026 with NO maximum staffing constraint.
Tests if removing the max constraint solves the infeasibility issue.
"""

import sys
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from entities import Base, Team, Employee, ShiftType, TeamShiftAssignment
from solver import plan_shifts_solver
import db_init

def setup_test_database():
    """Create in-memory database with test data but max staffing = 99"""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create shift types with NO max constraint (set to 99)
    shift_types = [
        ShiftType(
            id=1,
            name='F',
            description='Frühschicht',
            start_time='06:00',
            end_time='14:00',
            duration_hours=8,
            min_staff_weekday=4,
            max_staff_weekday=99,  # No max constraint!
            min_staff_weekend=2,
            max_staff_weekend=99   # No max constraint!
        ),
        ShiftType(
            id=2,
            name='S',
            description='Spätschicht',
            start_time='14:00',
            end_time='22:00',
            duration_hours=8,
            min_staff_weekday=3,
            max_staff_weekday=99,  # No max constraint!
            min_staff_weekend=2,
            max_staff_weekend=99   # No max constraint!
        ),
        ShiftType(
            id=3,
            name='N',
            description='Nachtschicht',
            start_time='22:00',
            end_time='06:00',
            duration_hours=8,
            min_staff_weekday=3,
            max_staff_weekday=99,  # No max constraint!
            min_staff_weekend=2,
            max_staff_weekend=99   # No max constraint!
        )
    ]
    for st in shift_types:
        session.add(st)
    
    # Create 3 teams
    teams = []
    for i, team_name in enumerate(['Alpha', 'Beta', 'Gamma'], start=1):
        team = Team(
            id=i,
            name=team_name,
            description=f'Team {team_name}'
        )
        teams.append(team)
        session.add(team)
    
    # Create 5 employees per team (15 total)
    employees = []
    emp_id = 1
    for team in teams:
        for j in range(5):
            emp = Employee(
                id=emp_id,
                Personalnummer=f'{team.name[0]}{j+1:03d}',
                Vorname=f'{team.name}_Employee',
                Nachname=f'{j+1}',
                team_id=team.id,
                weekly_hours=48,
                email=f'{team.name.lower()}{j+1}@test.com'
            )
            employees.append(emp)
            session.add(emp)
            emp_id += 1
    
    session.commit()
    return session

def test_january_2026_no_max():
    """Test January 2026 planning with max staffing = 99"""
    print("="*80)
    print("TESTING: January 2026 Shift Planning with NO MAX STAFFING CONSTRAINT")
    print("="*80)
    
    session = setup_test_database()
    
    # January 2026: Thursday Jan 1 - Saturday Jan 31 (31 days)
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    print(f"\nPlanning Period: {start_date} to {end_date}")
    print(f"Start: {start_date.strftime('%A, %B %d, %Y')}")
    print(f"End: {end_date.strftime('%A, %B %d, %Y')}")
    print(f"Days: {(end_date - start_date).days + 1}")
    print(f"\nMax Staffing per Shift: 99 (effectively unlimited)")
    
    # Get all data
    shift_types = session.query(ShiftType).all()
    teams = session.query(Team).all()
    employees = session.query(Employee).all()
    existing_assignments = session.query(TeamShiftAssignment).all()
    
    print(f"\nConfiguration:")
    print(f"  Teams: {len(teams)}")
    print(f"  Employees: {len(employees)} ({len(employees)//len(teams)} per team)")
    print(f"  Shift Types: {len(shift_types)}")
    
    for st in shift_types:
        print(f"    {st.name}: min={st.min_staff_weekday} (weekday), "
              f"max={st.max_staff_weekday} (weekday)")
    
    # Run solver
    print("\n" + "="*80)
    print("RUNNING SOLVER...")
    print("="*80)
    
    try:
        result = plan_shifts_solver(
            session=session,
            start_date=start_date,
            end_date=end_date,
            shift_types=shift_types,
            teams=teams,
            employees=employees,
            existing_team_shift_assignments=existing_assignments,
            locked_assignments=[]
        )
        
        print("\n" + "="*80)
        if result['status'] == 'OPTIMAL' or result['status'] == 'FEASIBLE':
            print(f"✓ RESULT: {result['status']}")
            print("="*80)
            print("\n🎉 SUCCESS! Removing max staffing constraint SOLVES the problem!")
            
            # Analyze the solution
            assignments = result['assignments']
            print(f"\nTotal Assignments: {len(assignments)}")
            
            # Count assignments per employee
            emp_assignments = {}
            for a in assignments:
                emp_id = a['employee_id']
                if emp_id not in emp_assignments:
                    emp_assignments[emp_id] = []
                emp_assignments[emp_id].append(a)
            
            print(f"\nEmployee Work Distribution:")
            total_days = 0
            for emp_id in sorted(emp_assignments.keys()):
                emp = next(e for e in employees if e.id == emp_id)
                days_worked = len(emp_assignments[emp_id])
                hours_worked = days_worked * 8
                total_days += days_worked
                print(f"  {emp.Personalnummer} ({emp.team.name}): {days_worked} days, "
                      f"{hours_worked}h")
            
            avg_days = total_days / len(employees)
            print(f"\nAverage: {avg_days:.1f} days per employee")
            print(f"Total person-days: {total_days}")
            
            # Check staffing levels per shift per day
            print(f"\nStaffing levels by shift:")
            from collections import defaultdict
            staffing = defaultdict(list)
            
            for a in assignments:
                key = (a['date'], a['shift_type_id'])
                if key not in staffing:
                    staffing[key] = []
                staffing[key].append(a['employee_id'])
            
            shift_stats = {st.id: [] for st in shift_types}
            for (d, st_id), emps in staffing.items():
                shift_stats[st_id].append(len(emps))
            
            for st in shift_types:
                counts = shift_stats[st.id]
                if counts:
                    print(f"  {st.name}: min={min(counts)}, max={max(counts)}, "
                          f"avg={sum(counts)/len(counts):.1f}")
            
            return True
            
        else:
            print(f"✗ RESULT: {result['status']}")
            print("="*80)
            print("\n❌ STILL INFEASIBLE even without max staffing constraint!")
            print("\nThis means the problem is NOT caused by max staffing limits.")
            print("The root cause is elsewhere (likely minimum hours + rotation pattern).")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_january_2026_no_max()
    sys.exit(0 if success else 1)
