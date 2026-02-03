#!/usr/bin/env python3
"""
Script to visualize the February 2026 shift schedule from the database
"""

import sqlite3
from datetime import date, timedelta
from collections import defaultdict

def get_schedule(db_path, start_date, end_date):
    """Fetch schedule from database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get employees with their teams
    cursor.execute("""
        SELECT e.Id, e.Vorname || ' ' || e.Name as FullName, e.Personalnummer, t.Name as TeamName
        FROM Employees e
        JOIN Teams t ON e.TeamId = t.Id
        ORDER BY t.Name, e.Name
    """)
    employees = {row[0]: {'name': row[1], 'pnr': row[2], 'team': row[3]} for row in cursor.fetchall()}
    
    # Get shift assignments
    cursor.execute("""
        SELECT sa.EmployeeId, sa.Date, st.Code
        FROM ShiftAssignments sa
        JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE sa.Date >= ? AND sa.Date <= ?
        ORDER BY sa.EmployeeId, sa.Date
    """, (start_date.isoformat(), end_date.isoformat()))
    
    assignments = defaultdict(dict)
    for emp_id, date_str, shift_code in cursor.fetchall():
        d = date.fromisoformat(date_str)
        assignments[emp_id][d] = shift_code
    
    conn.close()
    return employees, assignments

def print_schedule(employees, assignments, start_date, end_date):
    """Print schedule in table format"""
    # Generate date range
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)
    
    # Group employees by team
    teams = defaultdict(list)
    for emp_id, emp_info in employees.items():
        teams[emp_info['team']].append((emp_id, emp_info))
    
    # Print header
    print("\nSHIFT SCHEDULE - FEBRUARY 2026")
    print("=" * 120)
    print(f"{'Employee':<30}", end='')
    for d in dates:
        day_name = d.strftime('%a')[:2]
        print(f"{day_name} {d.day:2d}  ", end='')
    print()
    print("=" * 120)
    
    # Print by team
    for team_name in sorted(teams.keys()):
        print(f"\n{team_name}")
        print("-" * 120)
        
        for emp_id, emp_info in sorted(teams[team_name], key=lambda x: x[1]['name']):
            name = emp_info['name']
            pnr = emp_info['pnr']
            print(f"{name} ({pnr})"[:30].ljust(30), end='')
            
            for d in dates:
                shift = assignments[emp_id].get(d, '+')  # '+' means free day
                print(f"  {shift}   ", end='')
            print()
    
    print("=" * 120)
    
    # Print statistics for specific employees
    print("\nFOCUS: Lisa Meyer (PN004) and Max Müller (PN001)")
    print("-" * 80)
    
    for emp_id, emp_info in employees.items():
        if emp_info['pnr'] in ['PN004', 'PN001']:
            name = emp_info['name']
            pnr = emp_info['pnr']
            print(f"\n{name} ({pnr}):")
            
            # Check specific dates
            target_dates = [
                date(2026, 2, 11),  # Should have N shift
                date(2026, 2, 28),  # Should NOT have F shift
            ]
            
            for d in target_dates:
                shift = assignments[emp_id].get(d, '+')
                day_name = d.strftime('%A')
                print(f"  {day_name} {d.isoformat()}: {shift}")
            
            # Count shifts by week
            weeks = [
                (date(2026, 2, 2), date(2026, 2, 8)),
                (date(2026, 2, 9), date(2026, 2, 15)),
                (date(2026, 2, 16), date(2026, 2, 22)),
                (date(2026, 2, 23), date(2026, 2, 28)),
            ]
            
            print(f"\n  Shifts by week:")
            for week_start, week_end in weeks:
                shifts = []
                d = week_start
                while d <= week_end:
                    shift = assignments[emp_id].get(d, '+')
                    if shift != '+':
                        shifts.append(shift)
                    d += timedelta(days=1)
                print(f"    Week {week_start.strftime('%b %d')}-{week_end.strftime('%b %d')}: {len(shifts)} shifts")

if __name__ == '__main__':
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'test_dienstplan.db'
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 28)
    
    employees, assignments = get_schedule(db_path, start_date, end_date)
    print_schedule(employees, assignments, start_date, end_date)
