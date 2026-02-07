"""
Data loader for the shift planning system.
Generates sample data or loads from external sources.
"""

from datetime import date, timedelta
from typing import List, Tuple, Dict
from entities import (
    Employee, Team, Absence, AbsenceType,
    ShiftAssignment, STANDARD_SHIFT_TYPES
)


def generate_sample_data() -> Tuple[List[Employee], List[Team], List[Absence]]:
    """
    Generate sample data for testing the shift planning system.
    
    According to requirements:
    - 17 employees total
    - 3 teams with 5-6 members each
    - TD-qualified employees (combining BMT/BSB roles)
    - No virtual teams (removed from system)
    
    Returns:
        Tuple of (employees, teams, absences)
    """
    
    # Create 3 regular teams
    team_alpha = Team(id=1, name="Team Alpha", description="First team")
    team_beta = Team(id=2, name="Team Beta", description="Second team")
    team_gamma = Team(id=3, name="Team Gamma", description="Third team")
    
    teams = [team_alpha, team_beta, team_gamma]
    
    # Create employees (17 total in teams)
    employees = []
    
    # Team Alpha (5 members)
    employees.extend([
        Employee(1, "Max", "Müller", "1001", team_id=1),
        Employee(2, "Anna", "Schmidt", "1002", team_id=1),
        Employee(3, "Peter", "Weber", "1003", team_id=1),
        Employee(4, "Lisa", "Meyer", "1004", team_id=1),
        Employee(5, "Tom", "Wagner", "1005", team_id=1),
    ])
    
    # Team Beta (6 members)
    employees.extend([
        Employee(6, "Julia", "Becker", "2001", team_id=2),
        Employee(7, "Michael", "Schulz", "2002", team_id=2),
        Employee(8, "Sarah", "Hoffmann", "2003", team_id=2),
        Employee(9, "Daniel", "Koch", "2004", team_id=2),
        Employee(10, "Laura", "Bauer", "2005", team_id=2),
        Employee(17, "Thomas", "Zimmermann", "2006", team_id=2),
    ])
    
    # Team Gamma (6 members)
    employees.extend([
        Employee(11, "Markus", "Richter", "3001", team_id=3),
        Employee(12, "Stefanie", "Klein", "3002", team_id=3),
        Employee(13, "Andreas", "Wolf", "3003", team_id=3),
        Employee(14, "Nicole", "Schröder", "3004", team_id=3),
        Employee(15, "Christian", "Neumann", "3005", team_id=3),
        Employee(16, "Robert", "Franke", "1006", team_id=3, is_td_qualified=True),
    ])
    
    # Assign employees to teams
    for emp in employees:
        if emp.team_id == 1:
            team_alpha.employees.append(emp)
        elif emp.team_id == 2:
            team_beta.employees.append(emp)
        elif emp.team_id == 3:
            team_gamma.employees.append(emp)
    
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


def load_rotation_groups_from_db(db_path: str) -> Dict[int, List[str]]:
    """
    Load rotation patterns from RotationGroups and RotationGroupShifts tables.
    
    Returns a dictionary mapping rotation_group_id to a list of shift codes 
    in their rotation order.
    
    Example return value:
        {
            1: ["F", "N", "S"],      # Standard rotation
            2: ["F", "S"],            # Two-shift rotation
            3: ["N", "S", "F"]        # Different starting point
        }
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Dict mapping rotation_group_id to list of shift codes in rotation order
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    rotation_patterns = {}
    
    try:
        # Get all active rotation groups
        cursor.execute("""
            SELECT Id, Name 
            FROM RotationGroups 
            WHERE IsActive = 1
        """)
        rotation_groups = cursor.fetchall()
        
        for group_id, group_name in rotation_groups:
            # Get shifts for this rotation group in order
            cursor.execute("""
                SELECT st.Code
                FROM RotationGroupShifts rgs
                JOIN ShiftTypes st ON st.Id = rgs.ShiftTypeId
                WHERE rgs.RotationGroupId = ?
                ORDER BY rgs.RotationOrder ASC
            """, (group_id,))
            
            shifts = [row[0] for row in cursor.fetchall()]
            
            if shifts:  # Only add if group has shifts
                rotation_patterns[group_id] = shifts
            else:
                print(f"[!] Warning: Rotation group '{group_name}' (ID: {group_id}) has no shifts configured")
        
    except sqlite3.Error as e:
        print(f"[!] Error loading rotation groups from database: {e}")
        # Return empty dict on error - fallback to hardcoded pattern will be used
        return {}
    finally:
        conn.close()
    
    return rotation_patterns


def load_global_settings(db_path: str) -> Dict:
    """
    Load global shift planning settings from the database.
    
    Returns:
        Dict with global settings including:
        - max_consecutive_shifts_weeks: DEPRECATED - Now configured per shift type (ShiftType.max_consecutive_days)
        - max_consecutive_night_shifts_weeks: DEPRECATED - Now configured per shift type (ShiftType.max_consecutive_days)
        - min_rest_hours: Minimum rest hours between shifts (still used globally)
    
    Note: The max_consecutive_* values are kept for backward compatibility but are no longer
    used by the shift planning algorithm. Use ShiftType.max_consecutive_days instead.
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM GlobalSettings WHERE Id = 1")
        row = cursor.fetchone()
        
        if row:
            settings = {
                'max_consecutive_shifts_weeks': row['MaxConsecutiveShifts'],  # In weeks
                'max_consecutive_night_shifts_weeks': row['MaxConsecutiveNightShifts'],  # In weeks
                'min_rest_hours': row['MinRestHoursBetweenShifts']
            }
        else:
            # Default values if not found (same as DB defaults)
            settings = {
                'max_consecutive_shifts_weeks': 6,  # 6 weeks
                'max_consecutive_night_shifts_weeks': 3,  # 3 weeks
                'min_rest_hours': 11
            }
    except Exception as e:
        # If table doesn't exist or error, use defaults
        print(f"Warning: Could not load GlobalSettings from database: {e}")
        settings = {
            'max_consecutive_shifts_weeks': 6,
            'max_consecutive_night_shifts_weeks': 3,
            'min_rest_hours': 11
        }
    finally:
        conn.close()
    
    return settings


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
        SELECT Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode, WeeklyWorkingHours,
               MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend,
               WorksMonday, WorksTuesday, WorksWednesday, WorksThursday, WorksFriday,
               WorksSaturday, WorksSunday, MaxConsecutiveDays
        FROM ShiftTypes
        WHERE IsActive = 1
        ORDER BY Id
    """)
    shift_types = []
    for row in cursor.fetchall():
        # Handle missing columns for older database schemas
        try:
            weekly_hours = row['WeeklyWorkingHours']
        except (KeyError, IndexError):
            weekly_hours = 40.0  # Default to standard 40-hour work week
        
        try:
            min_staff_weekday = row['MinStaffWeekday']
            max_staff_weekday = row['MaxStaffWeekday']
            min_staff_weekend = row['MinStaffWeekend']
            max_staff_weekend = row['MaxStaffWeekend']
        except (KeyError, IndexError):
            # Default values if columns don't exist (for migration compatibility)
            # Max values set high to allow flexibility for cross-team assignments
            min_staff_weekday = 3
            max_staff_weekday = 20
            min_staff_weekend = 2
            max_staff_weekend = 20
        
        try:
            works_monday = bool(row['WorksMonday'])
            works_tuesday = bool(row['WorksTuesday'])
            works_wednesday = bool(row['WorksWednesday'])
            works_thursday = bool(row['WorksThursday'])
            works_friday = bool(row['WorksFriday'])
            works_saturday = bool(row['WorksSaturday'])
            works_sunday = bool(row['WorksSunday'])
        except (KeyError, IndexError):
            # Default: works all days (backwards compatibility)
            works_monday = works_tuesday = works_wednesday = True
            works_thursday = works_friday = works_saturday = works_sunday = True
        
        try:
            max_consecutive_days = row['MaxConsecutiveDays']
        except (KeyError, IndexError):
            # Default: 6 for most shifts, but will be migrated from GlobalSettings
            max_consecutive_days = 6
        
        shift_type = ShiftType(
            id=row['Id'],
            code=row['Code'],
            name=row['Name'],
            start_time=row['StartTime'],
            end_time=row['EndTime'],
            hours=row['DurationHours'],
            color_code=row['ColorCode'],
            weekly_working_hours=weekly_hours,
            min_staff_weekday=min_staff_weekday,
            max_staff_weekday=max_staff_weekday,
            min_staff_weekend=min_staff_weekend,
            max_staff_weekend=max_staff_weekend,
            works_monday=works_monday,
            works_tuesday=works_tuesday,
            works_wednesday=works_wednesday,
            works_thursday=works_thursday,
            works_friday=works_friday,
            works_saturday=works_saturday,
            works_sunday=works_sunday,
            max_consecutive_days=max_consecutive_days
        )
        shift_types.append(shift_type)
    
    # Load teams
    cursor.execute("SELECT Id, Name, Description, Email, IsVirtual, RotationGroupId FROM Teams")
    teams = []
    for row in cursor.fetchall():
        # IsVirtual column added in migration - default to False if not present
        try:
            is_virtual = bool(row['IsVirtual'])
        except (KeyError, IndexError):
            is_virtual = False
        
        # RotationGroupId column for database-driven rotation patterns
        # Note: None values from the database are intentionally preserved - they represent
        # teams without assigned rotation groups (will use fallback F→N→S pattern)
        try:
            rotation_group_id = row['RotationGroupId']
        except (KeyError, IndexError):
            # Column doesn't exist in schema (old database) - default to None
            rotation_group_id = None
        
        team = Team(id=row['Id'], name=row['Name'], description=row['Description'], 
                   email=row['Email'], is_virtual=is_virtual, rotation_group_id=rotation_group_id)
        teams.append(team)
    
    # Load TeamShiftAssignments (which shifts each team can work)
    cursor.execute("""
        SELECT TeamId, ShiftTypeId
        FROM TeamShiftAssignments
        ORDER BY TeamId
    """)
    team_shift_assignments = {}
    for row in cursor.fetchall():
        team_id = row['TeamId']
        shift_type_id = row['ShiftTypeId']
        if team_id not in team_shift_assignments:
            team_shift_assignments[team_id] = []
        team_shift_assignments[team_id].append(shift_type_id)
    
    # Assign allowed shift types to teams
    # IMPORTANT: If a team has no TeamShiftAssignments configured, automatically assign F, S, N
    # to enable standard rotation. This prevents INFEASIBLE issues where teams can't work
    # any of the required shifts (F, S, N).
    for team in teams:
        team.allowed_shift_type_ids = team_shift_assignments.get(team.id, [])
        
        # Auto-assign F, S, N to teams with empty configuration (backward compatibility)
        if not team.allowed_shift_type_ids and not team.is_virtual:
            # Find F, S, N shift type IDs from loaded shift types
            f_id = next((st.id for st in shift_types if st.code == "F"), None)
            s_id = next((st.id for st in shift_types if st.code == "S"), None)
            n_id = next((st.id for st in shift_types if st.code == "N"), None)
            
            # Only assign if all three shifts exist
            if f_id and s_id and n_id:
                team.allowed_shift_type_ids = [f_id, s_id, n_id]
                print(f"  Auto-assigned F, S, N shifts to {team.name} (no TeamShiftAssignments found)")
    
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
        
        team_id = row[COL_TEAM_ID]
        
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
