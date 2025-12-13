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
    
    Returns:
        Tuple of (employees, teams, absences)
    """
    
    # Create 3 teams
    team_alpha = Team(id=1, name="Team Alpha", description="First team")
    team_beta = Team(id=2, name="Team Beta", description="Second team")
    team_gamma = Team(id=3, name="Team Gamma", description="Third team")
    
    teams = [team_alpha, team_beta, team_gamma]
    
    # Create employees (15 regular + 2 springers + 2 special roles)
    employees = []
    
    # Team Alpha (5 members)
    employees.extend([
        Employee(1, "Max", "Müller", "1001", team_id=1),
        Employee(2, "Anna", "Schmidt", "1002", team_id=1, is_brandmeldetechniker=True),
        Employee(3, "Peter", "Weber", "1003", team_id=1),
        Employee(4, "Lisa", "Meyer", "1004", team_id=1, is_brandschutzbeauftragter=True),
        Employee(5, "Tom", "Wagner", "1005", team_id=1),
    ])
    
    # Team Beta (5 members)
    employees.extend([
        Employee(6, "Julia", "Becker", "2001", team_id=2, is_brandmeldetechniker=True),
        Employee(7, "Michael", "Schulz", "2002", team_id=2),
        Employee(8, "Sarah", "Hoffmann", "2003", team_id=2),
        Employee(9, "Daniel", "Koch", "2004", team_id=2, is_brandschutzbeauftragter=True),
        Employee(10, "Laura", "Bauer", "2005", team_id=2),
    ])
    
    # Team Gamma (5 members)
    employees.extend([
        Employee(11, "Markus", "Richter", "3001", team_id=3),
        Employee(12, "Stefanie", "Klein", "3002", team_id=3, is_brandmeldetechniker=True),
        Employee(13, "Andreas", "Wolf", "3003", team_id=3),
        Employee(14, "Nicole", "Schröder", "3004", team_id=3),
        Employee(15, "Christian", "Neumann", "3005", team_id=3, is_brandschutzbeauftragter=True),
    ])
    
    # Springers (backup workers - 4 people)
    employees.extend([
        Employee(16, "Robert", "Franke", "S001", is_springer=True, team_id=None),
        Employee(17, "Maria", "Lange", "S002", is_springer=True, team_id=None, is_brandmeldetechniker=True),
        Employee(18, "Thomas", "Zimmermann", "S003", is_springer=True, team_id=None),
        Employee(19, "Katharina", "Krüger", "S004", is_springer=True, team_id=None, is_brandschutzbeauftragter=True),
    ])
    
    # Assign employees to teams
    for emp in employees:
        if emp.team_id == 1:
            team_alpha.employees.append(emp)
        elif emp.team_id == 2:
            team_beta.employees.append(emp)
        elif emp.team_id == 3:
            team_gamma.employees.append(emp)
    
    # Create sample absences
    absences = []
    today = date.today()
    
    # Some vacation days
    absences.extend([
        Absence(1, 2, AbsenceType.URLAUB, today + timedelta(days=10), today + timedelta(days=14), "Jahresurlaub"),
        Absence(2, 7, AbsenceType.URLAUB, today + timedelta(days=20), today + timedelta(days=27), "Sommerurlaub"),
        Absence(3, 12, AbsenceType.LEHRGANG, today + timedelta(days=5), today + timedelta(days=7), "Fortbildung"),
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
        Tuple of (employees, teams, absences)
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load teams
    cursor.execute("SELECT Id, Name, Description, Email FROM Teams")
    teams = []
    for row in cursor.fetchall():
        team = Team(id=row[0], name=row[1], description=row[2], email=row[3])
        teams.append(team)
    
    # Load employees
    cursor.execute("""
        SELECT Id, Vorname, Name, Personalnummer, Email, Geburtsdatum, 
               Funktion, IsSpringer, IsFerienjobber, IsBrandmeldetechniker, 
               IsBrandschutzbeauftragter, TeamId
        FROM Employees
    """)
    employees = []
    for row in cursor.fetchall():
        emp = Employee(
            id=row[0],
            vorname=row[1],
            name=row[2],
            personalnummer=row[3],
            email=row[4],
            geburtsdatum=date.fromisoformat(row[5]) if row[5] else None,
            funktion=row[6],
            is_springer=bool(row[7]),
            is_ferienjobber=bool(row[8]),
            is_brandmeldetechniker=bool(row[9]),
            is_brandschutzbeauftragter=bool(row[10]),
            team_id=row[11]
        )
        employees.append(emp)
        
        # Assign to team
        if emp.team_id:
            for team in teams:
                if team.id == emp.team_id:
                    team.employees.append(emp)
                    break
    
    # Load absences
    cursor.execute("""
        SELECT Id, EmployeeId, Type, StartDate, EndDate, Notes
        FROM Absences
    """)
    absences = []
    for row in cursor.fetchall():
        absence_type_map = {1: AbsenceType.KRANK, 2: AbsenceType.URLAUB, 3: AbsenceType.LEHRGANG}
        absence = Absence(
            id=row[0],
            employee_id=row[1],
            absence_type=absence_type_map.get(row[2], AbsenceType.URLAUB),
            start_date=date.fromisoformat(row[3]),
            end_date=date.fromisoformat(row[4]),
            notes=row[5]
        )
        absences.append(absence)
    
    conn.close()
    
    return employees, teams, absences


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
               IsSpringerAssignment, IsFixed, Notes
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
            is_springer_assignment=bool(row[5]),
            is_fixed=bool(row[6]),
            notes=row[7]
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
            if emp.is_springer:
                qualifications.append("Springer")
            if emp.is_brandmeldetechniker:
                qualifications.append("BMT")
            if emp.is_brandschutzbeauftragter:
                qualifications.append("BSB")
            qual_str = f" ({', '.join(qualifications)})" if qualifications else ""
            print(f"  - {emp.full_name}{qual_str}")
