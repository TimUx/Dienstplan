"""
Manually create a valid schedule for January 2026 to demonstrate the system.
This bypasses the OR-Tools solver to create a simple, valid rotation schedule.
"""

import sqlite3
from datetime import date, datetime, timedelta

def create_manual_schedule():
    """Create manual schedule for January 2026"""
    
    db_path = "dienstplan.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing assignments for January 2026
    cursor.execute("DELETE FROM ShiftAssignments WHERE Date >= '2026-01-01' AND Date <= '2026-01-31'")
    
    # Get shift type IDs
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'F'")
    f_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'N'")
    n_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'S'")
    s_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'U'")
    u_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'L'")
    l_id = cursor.fetchone()[0]
    
    # Get team members
    cursor.execute("SELECT Id FROM Employees WHERE TeamId = 1 ORDER BY Id")  # Team Alpha
    team_alpha = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT Id FROM Employees WHERE TeamId = 2 ORDER BY Id")  # Team Beta
    team_beta = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT Id FROM Employees WHERE TeamId = 3 ORDER BY Id")  # Team Gamma
    team_gamma = [row[0] for row in cursor.fetchall()]
    
    print(f"Team Alpha: {team_alpha}")
    print(f"Team Beta: {team_beta}")
    print(f"Team Gamma: {team_gamma}")
    
    # Get absences
    cursor.execute("""
        SELECT EmployeeId, StartDate, EndDate, Type
        FROM Absences
        WHERE StartDate <= '2026-01-31' AND EndDate >= '2026-01-01'
    """)
    absences = cursor.fetchall()
    absence_dict = {}
    for emp_id, start, end, abs_type in absences:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        d = start_date
        while d <= end_date:
            if emp_id not in absence_dict:
                absence_dict[emp_id] = {}
            absence_dict[emp_id][d] = abs_type
            d += timedelta(days=1)
    
    print(f"Absences: {absence_dict}")
    
    # Define rotation: F → N → S for each week
    # Week starting Monday 2026-01-05: Alpha=F, Beta=N, Gamma=S
    # Week starting Monday 2026-01-12: Alpha=N, Beta=S, Gamma=F
    # Week starting Monday 2026-01-19: Alpha=S, Beta=F, Gamma=N
    # Week starting Monday 2026-01-26: Alpha=F, Beta=N, Gamma=S
    
    rotation = [
        # Week 0 (Thu 01.01 - Sun 04.01) - short week, same as week 1
        (date(2026, 1, 1), date(2026, 1, 4), {
            'Alpha': f_id, 'Beta': n_id, 'Gamma': s_id
        }),
        # Week 1 (Mon 05.01 - Sun 11.01)
        (date(2026, 1, 5), date(2026, 1, 11), {
            'Alpha': f_id, 'Beta': n_id, 'Gamma': s_id
        }),
        # Week 2 (Mon 12.01 - Sun 18.01)
        (date(2026, 1, 12), date(2026, 1, 18), {
            'Alpha': n_id, 'Beta': s_id, 'Gamma': f_id
        }),
        # Week 3 (Mon 19.01 - Sun 25.01)
        (date(2026, 1, 19), date(2026, 1, 25), {
            'Alpha': s_id, 'Beta': f_id, 'Gamma': n_id
        }),
        # Week 4 (Mon 26.01 - Sat 31.01)
        (date(2026, 1, 26), date(2026, 1, 31), {
            'Alpha': f_id, 'Beta': n_id, 'Gamma': s_id
        }),
    ]
    
    assignments = []
    
    for start_date, end_date, week_shifts in rotation:
        current_date = start_date
        while current_date <= end_date:
            is_weekend = current_date.weekday() >= 5  # Saturday=5, Sunday=6
            
            # Team Alpha assignments
            for emp_id in team_alpha:
                if emp_id in absence_dict and current_date in absence_dict[emp_id]:
                    # Employee is absent - assign absence type
                    shift_id = l_id if absence_dict[emp_id][current_date] == 3 else u_id
                    assignments.append((emp_id, shift_id, current_date.isoformat()))
                else:
                    # Assign team shift - on weekends, assign 4 out of 5 team members
                    if is_weekend:
                        if emp_id != team_alpha[0]:  # Skip first member on weekend
                            assignments.append((emp_id, week_shifts['Alpha'], current_date.isoformat()))
                    else:
                        # Weekday - all team members work
                        assignments.append((emp_id, week_shifts['Alpha'], current_date.isoformat()))
            
            # Team Beta assignments
            for emp_id in team_beta:
                if emp_id in absence_dict and current_date in absence_dict[emp_id]:
                    shift_id = l_id if absence_dict[emp_id][current_date] == 3 else u_id
                    assignments.append((emp_id, shift_id, current_date.isoformat()))
                else:
                    if is_weekend:
                        if emp_id != team_beta[0]:  # Skip first member on weekend
                            assignments.append((emp_id, week_shifts['Beta'], current_date.isoformat()))
                    else:
                        assignments.append((emp_id, week_shifts['Beta'], current_date.isoformat()))
            
            # Team Gamma assignments
            for emp_id in team_gamma:
                if emp_id in absence_dict and current_date in absence_dict[emp_id]:
                    shift_id = l_id if absence_dict[emp_id][current_date] == 3 else u_id
                    assignments.append((emp_id, shift_id, current_date.isoformat()))
                else:
                    if is_weekend:
                        if emp_id != team_gamma[0]:  # Skip first member on weekend
                            assignments.append((emp_id, week_shifts['Gamma'], current_date.isoformat()))
                    else:
                        assignments.append((emp_id, week_shifts['Gamma'], current_date.isoformat()))
            
            current_date += timedelta(days=1)
    
    # Insert assignments
    for emp_id, shift_id, date_str in assignments:
        cursor.execute("""
            INSERT INTO ShiftAssignments 
            (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, 0, 0, ?, 'Manual Script')
        """, (emp_id, shift_id, date_str, datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Created {len(assignments)} shift assignments for January 2026")
    print("\nRotation pattern (F → N → S):")
    print("  Week 01.01-04.01: Alpha=F, Beta=N, Gamma=S")
    print("  Week 05.01-11.01: Alpha=F, Beta=N, Gamma=S")
    print("  Week 12.01-18.01: Alpha=N, Beta=S, Gamma=F")
    print("  Week 19.01-25.01: Alpha=S, Beta=F, Gamma=N")
    print("  Week 26.01-31.01: Alpha=F, Beta=N, Gamma=S")

if __name__ == "__main__":
    create_manual_schedule()
