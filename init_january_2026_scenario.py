"""
Custom initialization script for January 2026 test scenario.
Creates exactly:
- 3 Teams
- 5 Employees per team
- Shift rotation F -> N -> S
- Weekday coverage: F: 4-10, S: 3-10, N: 2-10
- Weekend coverage: all 2-10
- 48h work week
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, date

def hash_password(password: str) -> str:
    """Simple password hashing for testing"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"

def init_january_2026_scenario(db_path: str = "dienstplan.db"):
    """Initialize database with January 2026 test scenario"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create schema first
    from db_init import create_database_schema
    create_database_schema(db_path)
    
    print("Creating January 2026 Test Scenario...")
    print("=" * 60)
    
    # Clear existing data
    cursor.execute("DELETE FROM ShiftAssignments")
    cursor.execute("DELETE FROM Absences")
    cursor.execute("DELETE FROM TeamShiftAssignments")
    cursor.execute("DELETE FROM Employees")
    cursor.execute("DELETE FROM Teams")
    cursor.execute("DELETE FROM ShiftTypes")
    cursor.execute("DELETE FROM AspNetRoles")
    cursor.execute("DELETE FROM AspNetUserRoles")
    cursor.execute("DELETE FROM AspNetUsers")
    cursor.execute("DELETE FROM GlobalSettings")
    
    # Create roles
    cursor.execute("INSERT INTO AspNetRoles (Id, Name, NormalizedName) VALUES (?, ?, ?)",
                   ("1", "Admin", "ADMIN"))
    cursor.execute("INSERT INTO AspNetRoles (Id, Name, NormalizedName) VALUES (?, ?, ?)",
                   ("2", "Mitarbeiter", "MITARBEITER"))
    
    # Create admin user
    admin_id = secrets.token_hex(16)
    admin_password_hash = hash_password("Admin123!")
    cursor.execute("""
        INSERT INTO AspNetUsers 
        (Id, Email, NormalizedEmail, PasswordHash, SecurityStamp, FullName, CreatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (admin_id, "admin@fritzwinter.de", "ADMIN@FRITZWINTER.DE", 
          admin_password_hash, secrets.token_hex(16), "Administrator", 
          datetime.utcnow().isoformat()))
    
    cursor.execute("INSERT INTO AspNetUserRoles (UserId, RoleId) VALUES (?, ?)",
                   (admin_id, "1"))
    
    # Create GlobalSettings with relaxed constraints
    cursor.execute("""
        INSERT INTO GlobalSettings 
        (Id, MaxConsecutiveShifts, MaxConsecutiveNightShifts, MinRestHoursBetweenShifts)
        VALUES (1, 6, 3, 11)
    """)
    
    print("✓ Created GlobalSettings: MaxConsecutiveShifts=6 weeks, MaxConsecutiveNightShifts=3 weeks, MinRest=11h")
    
    # Create 3 Teams
    teams = [
        ("Team Alpha", "Früh-Team"),
        ("Team Beta", "Nacht-Team"),
        ("Team Gamma", "Spät-Team")
    ]
    
    for name, desc in teams:
        cursor.execute("""
            INSERT INTO Teams (Name, Description, IsVirtual, CreatedAt)
            VALUES (?, ?, 0, ?)
        """, (name, desc, datetime.utcnow().isoformat()))
    
    print("✓ Created 3 Teams: Alpha, Beta, Gamma")
    
    # Create Shift Types with specific requirements
    # F = Früh (Early), S = Spät (Late), N = Nacht (Night)
    shift_types = [
        # Code, Name, Start, End, Hours, Color, MinWeekday, MaxWeekday, MinWeekend, MaxWeekend
        ("F", "Frühschicht", "05:45", "13:45", 8.0, "#FFD700", 4, 10, 2, 10),
        ("S", "Spätschicht", "13:45", "21:45", 8.0, "#FF8C00", 3, 10, 2, 10),
        ("N", "Nachtschicht", "21:45", "05:45", 8.0, "#4169E1", 2, 10, 2, 10),
        ("Z", "Zusatzschicht", "05:45", "13:45", 8.0, "#32CD32", 0, 5, 0, 5),
        ("BMT", "Brandmeldetechniker", "07:00", "15:00", 8.0, "#DC143C", 1, 1, 0, 0),
        ("BSB", "Brandschutzbeauftragter", "07:00", "15:00", 8.0, "#8B0000", 1, 1, 0, 0),
        ("K", "Krank", "00:00", "00:00", 0.0, "#808080", 0, 0, 0, 0),
        ("U", "Urlaub", "00:00", "00:00", 0.0, "#87CEEB", 0, 0, 0, 0),
        ("L", "Lehrgang", "00:00", "00:00", 0.0, "#DDA0DD", 0, 0, 0, 0),
    ]
    
    for code, name, start, end, hours, color, min_wd, max_wd, min_we, max_we in shift_types:
        cursor.execute("""
            INSERT INTO ShiftTypes 
            (Code, Name, StartTime, EndTime, DurationHours, ColorCode, IsActive,
             WorksMonday, WorksTuesday, WorksWednesday, WorksThursday, WorksFriday,
             WorksSaturday, WorksSunday, WeeklyWorkingHours,
             MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1, 1, 1, 1, 1, 1, 48.0, ?, ?, ?, ?, ?)
        """, (code, name, start, end, hours, color, min_wd, max_wd, min_we, max_we,
              datetime.utcnow().isoformat()))
    
    print("✓ Created Shift Types: F (4-10/2-10), S (3-10/2-10), N (2-10/2-10)")
    print("✓ Work week: 48h")
    
    # Create 5 employees per team (15 total)
    employees = [
        # Team Alpha (TeamId=1)
        ("Max", "Müller", "MA001", "max.mueller@example.com", 1, 0, 0, 0),
        ("Anna", "Schmidt", "MA002", "anna.schmidt@example.com", 1, 0, 0, 0),
        ("Peter", "Weber", "MA003", "peter.weber@example.com", 1, 0, 0, 0),
        ("Lisa", "Meyer", "MA004", "lisa.meyer@example.com", 1, 0, 1, 0),  # BMT qualified for TD
        ("Tom", "Wagner", "MA005", "tom.wagner@example.com", 1, 0, 0, 0),
        
        # Team Beta (TeamId=2)
        ("Julia", "Becker", "MA006", "julia.becker@example.com", 2, 0, 0, 0),
        ("Michael", "Schulz", "MA007", "michael.schulz@example.com", 2, 0, 0, 1),  # BSB qualified for TD
        ("Sarah", "Hoffmann", "MA008", "sarah.hoffmann@example.com", 2, 0, 0, 0),
        ("Daniel", "Koch", "MA009", "daniel.koch@example.com", 2, 0, 0, 0),
        ("Laura", "Bauer", "MA010", "laura.bauer@example.com", 2, 0, 0, 0),
        
        # Team Gamma (TeamId=3)
        ("Markus", "Richter", "MA011", "markus.richter@example.com", 3, 0, 0, 0),
        ("Stefanie", "Klein", "MA012", "stefanie.klein@example.com", 3, 0, 1, 0),  # BMT qualified for TD
        ("Andreas", "Wolf", "MA013", "andreas.wolf@example.com", 3, 0, 0, 0),
        ("Nicole", "Schröder", "MA014", "nicole.schroeder@example.com", 3, 0, 0, 0),
        ("Christian", "Neumann", "MA015", "christian.neumann@example.com", 3, 0, 0, 0),
    ]
    
    for vorname, name, pnr, email, team_id, is_springer, is_bmt, is_bsb in employees:
        pwd_hash = hash_password("Password123!")
        # TD qualified is set based on BMT OR BSB qualifications
        is_td = 1 if (is_bmt or is_bsb) else 0
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash,
             SecurityStamp, TeamId, IsSpringer, IsTdQualified, IsBrandmeldetechniker,
             IsBrandschutzbeauftragter, IsActive, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (vorname, name, pnr, email, email.upper(), pwd_hash, 
              secrets.token_hex(16), team_id, is_springer, is_td, is_bmt, is_bsb,
              datetime.utcnow().isoformat()))
    
    print(f"✓ Created 15 Employees (5 per team)")
    print("  - Team Alpha: 5 employees (1 TD-qualified: Lisa Meyer, BMT)")
    print("  - Team Beta: 5 employees (1 TD-qualified: Michael Schulz, BSB)")
    print("  - Team Gamma: 5 employees (1 TD-qualified: Stefanie Klein, BMT)")
    
    # Add some sample absences for January 2026
    # Type mapping: 1=AU (Krank), 2=U (Urlaub), 3=L (Lehrgang)
    absences = [
        # (EmployeeId, Type, StartDate, EndDate, Notes)
        (2, 2, "2026-01-13", "2026-01-17", "Urlaub"),  # Anna Schmidt - Urlaub
        (7, 3, "2026-01-20", "2026-01-22", "Lehrgang"),  # Michael Schulz - Lehrgang
    ]
    
    for emp_id, abs_type, start, end, notes in absences:
        cursor.execute("""
            INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (emp_id, abs_type, start, end, notes, datetime.utcnow().isoformat()))
    
    print(f"✓ Created 2 absences:")
    print("  - Anna Schmidt: Urlaub 13.-17.01.2026")
    print("  - Michael Schulz: Lehrgang 20.-22.01.2026")
    
    # Get shift type IDs for F, N, S
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'F'")
    f_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'N'")
    n_id = cursor.fetchone()[0]
    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'S'")
    s_id = cursor.fetchone()[0]
    
    # Assign all 3 shift types (F, N, S) to all teams
    # This allows the system to rotate teams through the shifts
    for team_id in [1, 2, 3]:  # Alpha, Beta, Gamma
        for shift_id in [f_id, n_id, s_id]:
            cursor.execute("""
                INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedAt)
                VALUES (?, ?, ?)
            """, (team_id, shift_id, datetime.utcnow().isoformat()))
    
    print("✓ Configured Team Shift Assignments: All teams can work F, N, S")
    print("  - This enables weekly rotation: F → N → S")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✓ Database initialized successfully!")
    print(f"✓ Database: {db_path}")
    print("\n🔑 Admin Login:")
    print("   Email: admin@fritzwinter.de")
    print("   Password: Admin123!")
    print("=" * 60)

if __name__ == "__main__":
    init_january_2026_scenario()
