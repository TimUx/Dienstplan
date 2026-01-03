"""
Data loader for the shift planning system.
Generates sample data or loads from external sources.
"""

from datetime import date, timedelta
from typing import List, Tuple
from entities import (
    Employee, Team, Absence, AbsenceType,
    ShiftAssignment, STANDARD_SHIFT_TYPES
)


def generate_sample_data() -> Tuple[List[Employee], List[Team], List[Absence]]:
    """
    Generate sample data for testing the shift planning system.
    
    According to requirements:
    - 17 employees total
    - 3 teams with 5 members each (15 employees)
    - 2 additional regular team members (not fixed as Springers)
    - TD-qualified employees (combining BMT/BSB roles)
    - Virtual team "Fire Alarm System" for TD-qualified employees without regular teams
    
    Returns:
        Tuple of (employees, teams, absences)
    """
    
    # Create 3 regular teams
    team_alpha = Team(id=1, name="Team Alpha", description="First team")
    team_beta = Team(id=2, name="Team Beta", description="Second team")
    team_gamma = Team(id=3, name="Team Gamma", description="Third team")
    
    # Create virtual team for Fire Alarm System (TD-qualified without regular team)
    team_fire_alarm = Team(id=99, name="Brandmeldeanlage", 
                          description="Virtuelles Team für Mitarbeiter mit Sonderfunktion (BMT/BSB) ohne reguläre Teamzuweisung",
                          is_virtual=True)  # Mark as virtual team
    
    teams = [team_alpha, team_beta, team_gamma, team_fire_alarm]
    
    # Create employees (15 in teams + 2 additional = 17 total)
    employees = []
    
    # Team Alpha (5 members)
    employees.extend([
        Employee(1, "Max", "Müller", "1001", team_id=1),
        Employee(2, "Anna", "Schmidt", "1002", team_id=1),
        Employee(3, "Peter", "Weber", "1003", team_id=1),
        Employee(4, "Lisa", "Meyer", "1004", team_id=1),
        Employee(5, "Tom", "Wagner", "1005", team_id=1),
    ])
    
    # Team Beta (5 members)
    employees.extend([
        Employee(6, "Julia", "Becker", "2001", team_id=2),
        Employee(7, "Michael", "Schulz", "2002", team_id=2),
        Employee(8, "Sarah", "Hoffmann", "2003", team_id=2),
        Employee(9, "Daniel", "Koch", "2004", team_id=2),
        Employee(10, "Laura", "Bauer", "2005", team_id=2),
    ])
    
    # Team Gamma (5 members)
    employees.extend([
        Employee(11, "Markus", "Richter", "3001", team_id=3),
        Employee(12, "Stefanie", "Klein", "3002", team_id=3),
        Employee(13, "Andreas", "Wolf", "3003", team_id=3),
        Employee(14, "Nicole", "Schröder", "3004", team_id=3),
        Employee(15, "Christian", "Neumann", "3005", team_id=3),
    ])
    
    # Additional employees - assigned to teams as regular members
    # One is TD-qualified and assigned to virtual "Fire Alarm System" team
    # The other is a regular team member
    employees.extend([
        Employee(16, "Robert", "Franke", "1006", team_id=99, is_td_qualified=True),
        Employee(17, "Thomas", "Zimmermann", "2006", team_id=2),  # Added to Team Beta
    ])
    
    # Assign employees to teams
    for emp in employees:
        if emp.team_id == 1:
            team_alpha.employees.append(emp)
        elif emp.team_id == 2:
            team_beta.employees.append(emp)
        elif emp.team_id == 3:
            team_gamma.employees.append(emp)
        elif emp.team_id == 99:
            team_fire_alarm.employees.append(emp)
    
    # Create sample absences using official codes: U, AU, L
    absences = []
    today = date.today()
    
    # Use official absence codes: U (Urlaub), AU (Krank), L (Lehrgang)
    absences.extend([
        Absence(1, 2, AbsenceType.U, today + timedelta(days=10), today + timedelta(days=14), "Jahresurlaub"),
        Absence(2, 7, AbsenceType.U, today + timedelta(days=20), today + timedelta(days=27), "Sommerurlaub"),
        Absence(3, 12, AbsenceType.L, today + timedelta(days=5), today + timedelta(days=7), "Fortbildung"),
    ])
    
    return employees, teams, absences


def load_from_database(db_path: str = "dienstplan.db"):
    """
    Load data from SQLite database (compatibility with .NET version).
    
    This function would connect to the existing SQLite database
    created by the .NET application and load the data.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Tuple of (employees, teams, absences, shift_types)
    """
    import sqlite3
    from entities import ShiftType
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable access by column name
    cursor = conn.cursor()
    
    # Load shift types from database
    cursor.execute("""
        SELECT Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode, WeeklyWorkingHours
        FROM ShiftTypes
        WHERE IsActive = 1
        ORDER BY Id
    """)
    shift_types = []
    for row in cursor.fetchall():
        shift_type = ShiftType(
            id=row['Id'],
            code=row['Code'],
            name=row['Name'],
            start_time=row['StartTime'],
            end_time=row['EndTime'],
            hours=row['DurationHours'],
            color_code=row['ColorCode'],
            weekly_working_hours=row['WeeklyWorkingHours']
        )
        shift_types.append(shift_type)
    
    # Load teams
    cursor.execute("SELECT Id, Name, Description, Email, IsVirtual FROM Teams")
    teams = []
    for row in cursor.fetchall():
        # IsVirtual column added in migration - default to False if not present
        is_virtual = bool(row['IsVirtual']) if 'IsVirtual' in row.keys() else False
        team = Team(id=row['Id'], name=row['Name'], description=row['Description'], 
                   email=row['Email'], is_virtual=is_virtual)
        teams.append(team)
    
    # Load employees
    cursor.execute("""
        SELECT Id, Vorname, Name, Personalnummer, Email, Geburtsdatum, 
               Funktion, IsFerienjobber, IsBrandmeldetechniker, 
               IsBrandschutzbeauftragter, TeamId
        FROM Employees
    """)
    employees = []
    
    # Define column indices for clarity
    COL_ID = 0
    COL_VORNAME = 1
    COL_NAME = 2
    COL_PERSONALNUMMER = 3
    COL_EMAIL = 4
    COL_GEBURTSDATUM = 5
    COL_FUNKTION = 6
    COL_IS_FERIENJOBBER = 7
    COL_IS_BMT = 8
    COL_IS_BSB = 9
    COL_TEAM_ID = 10
    
    for row in cursor.fetchall():
        # TD qualification: employee is qualified if they have either BMT or BSB qualification
        is_td = bool(row[COL_IS_BMT]) or bool(row[COL_IS_BSB])
        
        # Auto-assign Ferienjobbers to virtual Ferienjobber team (ID 98)
        team_id = row[COL_TEAM_ID]
        if bool(row[COL_IS_FERIENJOBBER]) and not team_id:
            team_id = 98  # Ferienjobber virtual team
        
        emp = Employee(
            id=row[COL_ID],
            vorname=row[COL_VORNAME],
            name=row[COL_NAME],
            personalnummer=row[COL_PERSONALNUMMER],
            email=row[COL_EMAIL],
            geburtsdatum=date.fromisoformat(row[COL_GEBURTSDATUM]) if row[COL_GEBURTSDATUM] else None,
            funktion=row[COL_FUNKTION],
            is_ferienjobber=bool(row[COL_IS_FERIENJOBBER]),
            is_brandmeldetechniker=bool(row[COL_IS_BMT]),
            is_brandschutzbeauftragter=bool(row[COL_IS_BSB]),
            is_td_qualified=is_td,
            team_id=team_id
        )
        employees.append(emp)
        
        # Assign to team
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    team.employees.append(emp)
                    break
    
    # Load absences with official code mapping
    # Map database Type values to official AbsenceType codes
    # Old: 1=KRANK, 2=URLAUB, 3=LEHRGANG
    # New: AU=Sick, U=Vacation, L=Training
    cursor.execute("""
        SELECT Id, EmployeeId, Type, StartDate, EndDate, Notes
        FROM Absences
    """)
    absences = []
    for row in cursor.fetchall():
        # Map old integer types to new official codes
        absence_type_map = {
            1: AbsenceType.AU,  # Krank -> AU
            2: AbsenceType.U,   # Urlaub -> U
            3: AbsenceType.L    # Lehrgang -> L
        }
        absence = Absence(
            id=row[0],
            employee_id=row[1],
            absence_type=absence_type_map.get(row[2], AbsenceType.U),
            start_date=date.fromisoformat(row[3]),
            end_date=date.fromisoformat(row[4]),
            notes=row[5]
        )
        absences.append(absence)
    
    # Load approved vacation requests and convert them to absences
    # This ensures the solver considers them when creating shift plans
    cursor.execute("""
        SELECT Id, EmployeeId, StartDate, EndDate, Notes
        FROM VacationRequests
        WHERE Status = 'Genehmigt'
    """)
    vacation_id_offset = 10000  # Offset to avoid ID conflicts with Absences table
    for row in cursor.fetchall():
        absence = Absence(
            id=vacation_id_offset + row[0],
            employee_id=row[1],
            absence_type=AbsenceType.U,  # Approved vacation -> U
            start_date=date.fromisoformat(row[2]),
            end_date=date.fromisoformat(row[3]),
            notes=row[4] or "Genehmigter Urlaub"
        )
        absences.append(absence)
    
    conn.close()
    
    return employees, teams, absences, shift_types


def get_existing_assignments(db_path: str, start_date: date, end_date: date) -> List[ShiftAssignment]:
    """
    Load existing shift assignments from database for a date range.
    
    Args:
        db_path: Path to the SQLite database file
        start_date: Start date of the range
        end_date: End date of the range
        
    Returns:
        List of existing shift assignments
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Id, EmployeeId, ShiftTypeId, Date, IsManual, 
               IsFixed, Notes
        FROM ShiftAssignments
        WHERE Date >= ? AND Date <= ?
    """, (start_date.isoformat(), end_date.isoformat()))
    
    assignments = []
    for row in cursor.fetchall():
        assignment = ShiftAssignment(
            id=row[0],
            employee_id=row[1],
            shift_type_id=row[2],
            date=date.fromisoformat(row[3]),
            is_manual=bool(row[4]),
            is_fixed=bool(row[5]),
            notes=row[6]
        )
        assignments.append(assignment)
    
    conn.close()
    
    return assignments


if __name__ == "__main__":
    # Test data generation
    employees, teams, absences = generate_sample_data()
    
    print(f"Generated {len(employees)} employees in {len(teams)} teams")
    print(f"Generated {len(absences)} absences")
    
    for team in teams:
        print(f"\n{team.name}: {len(team.employees)} members")
        for emp in team.employees:
            qualifications = []
            if emp.is_td_qualified:
                qualifications.append("TD")
            if emp.is_brandmeldetechniker:
                qualifications.append("BMT")
            if emp.is_brandschutzbeauftragter:
                qualifications.append("BSB")
            qual_str = f" ({', '.join(qualifications)})" if qualifications else ""
            print(f"  - {emp.full_name}{qual_str}")
