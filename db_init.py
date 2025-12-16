"""
Database initialization script for Dienstplan system.
Creates all necessary tables and initializes with sample data if needed.
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime


def create_database_schema(db_path: str = "dienstplan.db"):
    """
    Create all database tables.
    
    Args:
        db_path: Path to SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Teams (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Description TEXT,
            Email TEXT,
            IsVirtual INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Employees (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT NOT NULL UNIQUE,
            Email TEXT,
            Geburtsdatum TEXT,
            Funktion TEXT,
            IsSpringer INTEGER NOT NULL DEFAULT 0,
            IsFerienjobber INTEGER NOT NULL DEFAULT 0,
            IsBrandmeldetechniker INTEGER NOT NULL DEFAULT 0,
            IsBrandschutzbeauftragter INTEGER NOT NULL DEFAULT 0,
            IsTdQualified INTEGER NOT NULL DEFAULT 0,
            TeamId INTEGER,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (TeamId) REFERENCES Teams(Id)
        )
    """)
    
    # ShiftTypes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ShiftTypes (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Code TEXT NOT NULL UNIQUE,
            Name TEXT NOT NULL,
            StartTime TEXT NOT NULL,
            EndTime TEXT NOT NULL,
            DurationHours REAL NOT NULL,
            ColorCode TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ShiftAssignments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ShiftAssignments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            ShiftTypeId INTEGER NOT NULL,
            Date TEXT NOT NULL,
            IsManual INTEGER NOT NULL DEFAULT 0,
            IsSpringerAssignment INTEGER NOT NULL DEFAULT 0,
            IsFixed INTEGER NOT NULL DEFAULT 0,
            Notes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            ModifiedAt TEXT,
            ModifiedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id)
        )
    """)
    
    # Absences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Absences (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            Type INTEGER NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Notes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    # AspNetUsers table (for authentication)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AspNetUsers (
            Id TEXT PRIMARY KEY,
            Email TEXT NOT NULL UNIQUE,
            NormalizedEmail TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL,
            SecurityStamp TEXT NOT NULL,
            FullName TEXT,
            LockoutEnd TEXT,
            AccessFailedCount INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # AspNetRoles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AspNetRoles (
            Id TEXT PRIMARY KEY,
            Name TEXT NOT NULL UNIQUE,
            NormalizedName TEXT NOT NULL UNIQUE
        )
    """)
    
    # AspNetUserRoles table (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AspNetUserRoles (
            UserId TEXT NOT NULL,
            RoleId TEXT NOT NULL,
            PRIMARY KEY (UserId, RoleId),
            FOREIGN KEY (UserId) REFERENCES AspNetUsers(Id),
            FOREIGN KEY (RoleId) REFERENCES AspNetRoles(Id)
        )
    """)
    
    # VacationRequests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VacationRequests (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Status TEXT NOT NULL DEFAULT 'InBearbeitung',
            Notes TEXT,
            DisponentResponse TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            ProcessedAt TEXT,
            ProcessedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    # ShiftExchanges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ShiftExchanges (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ShiftAssignmentId INTEGER NOT NULL,
            OfferingEmployeeId INTEGER NOT NULL,
            RequestingEmployeeId INTEGER,
            Status TEXT NOT NULL DEFAULT 'Angeboten',
            OfferingReason TEXT,
            DisponentNotes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ProcessedAt TEXT,
            ProcessedBy TEXT,
            FOREIGN KEY (ShiftAssignmentId) REFERENCES ShiftAssignments(Id),
            FOREIGN KEY (OfferingEmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (RequestingEmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    # AuditLogs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AuditLogs (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UserId TEXT,
            UserName TEXT,
            EntityName TEXT NOT NULL,
            EntityId TEXT NOT NULL,
            Action TEXT NOT NULL,
            Changes TEXT,
            FOREIGN KEY (UserId) REFERENCES AspNetUsers(Id)
        )
    """)
    
    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employees_personalnummer 
        ON Employees(Personalnummer)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shiftassignments_date 
        ON ShiftAssignments(Date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shiftassignments_employee 
        ON ShiftAssignments(EmployeeId, Date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_absences_employee_date 
        ON Absences(EmployeeId, StartDate, EndDate)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditlogs_timestamp 
        ON AuditLogs(Timestamp DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditlogs_entity 
        ON AuditLogs(EntityName, EntityId)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database schema created successfully: {db_path}")


def initialize_default_roles(db_path: str = "dienstplan.db"):
    """Initialize default roles (Admin, Disponent, Mitarbeiter)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    roles = [
        ("admin-role-id", "Admin", "ADMIN"),
        ("disponent-role-id", "Disponent", "DISPONENT"),
        ("mitarbeiter-role-id", "Mitarbeiter", "MITARBEITER")
    ]
    
    for role_id, name, normalized in roles:
        cursor.execute("""
            INSERT OR IGNORE INTO AspNetRoles (Id, Name, NormalizedName)
            VALUES (?, ?, ?)
        """, (role_id, name, normalized))
    
    conn.commit()
    conn.close()
    print("✅ Default roles initialized")


def hash_password(password: str) -> str:
    """
    Simple password hashing using SHA256.
    
    Note: This matches the web_api.py implementation for consistency.
    For production, consider upgrading to bcrypt, scrypt, or Argon2.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def create_default_admin(db_path: str = "dienstplan.db"):
    """Create default admin user"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    admin_id = "admin-user-id"
    admin_email = "admin@fritzwinter.de"
    admin_password = "Admin123!"
    
    # Check if admin already exists
    cursor.execute("SELECT Id FROM AspNetUsers WHERE Email = ?", (admin_email,))
    if cursor.fetchone():
        print("⚠️  Admin user already exists")
        conn.close()
        return
    
    # Create admin user
    password_hash = hash_password(admin_password)
    security_stamp = secrets.token_hex(16)
    
    cursor.execute("""
        INSERT INTO AspNetUsers (Id, Email, NormalizedEmail, PasswordHash, SecurityStamp, FullName)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (admin_id, admin_email, admin_email.upper(), password_hash, security_stamp, "Administrator"))
    
    # Assign Admin role
    cursor.execute("""
        INSERT INTO AspNetUserRoles (UserId, RoleId)
        VALUES (?, ?)
    """, (admin_id, "admin-role-id"))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Default admin user created:")
    print(f"   Email: {admin_email}")
    print(f"   Password: {admin_password}")
    print(f"   ⚠️  CHANGE THIS PASSWORD AFTER FIRST LOGIN!")


def initialize_shift_types(db_path: str = "dienstplan.db"):
    """
    Initialize standard shift types.
    
    Official absence codes (U, AU, L) are stored in Absences table,
    NOT as shift types. Shift types are only for actual work shifts.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    shift_types = [
        (1, "F", "Früh", "05:45", "13:45", 8.0, "#4CAF50"),
        (2, "S", "Spät", "13:45", "21:45", 8.0, "#FF9800"),
        (3, "N", "Nacht", "21:45", "05:45", 8.0, "#2196F3"),
        (4, "Z", "Zwischendienst", "08:00", "16:00", 8.0, "#9C27B0"),
        (5, "BMT", "Brandmeldetechniker", "06:00", "14:00", 8.0, "#F44336"),
        (6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", 9.5, "#E91E63"),
        (7, "TD", "Tagdienst", "06:00", "16:30", 10.5, "#673AB7"),
        # REMOVED: "K" (Krank) and old "U" (Urlaub) shift types
        # Absences are now handled exclusively through Absences table with codes: U, AU, L
    ]
    
    for shift_type in shift_types:
        cursor.execute("""
            INSERT OR IGNORE INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, shift_type)
    
    conn.commit()
    conn.close()
    print("✅ Standard shift types initialized (absences use separate codes: U, AU, L)")


def initialize_sample_teams(db_path: str = "dienstplan.db"):
    """
    Initialize sample teams.
    
    CRITICAL: 
    - No virtual "Springer Team" - springers are employees with is_springer attribute
    - Virtual team "Fire Alarm System" (ID 99) for display grouping of TD-qualified employees
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    teams = [
        ("Team Alpha", "Erste Schichtgruppe", "team.alpha@fritzwinter.de", 0),
        ("Team Beta", "Zweite Schichtgruppe", "team.beta@fritzwinter.de", 0),
        ("Team Gamma", "Dritte Schichtgruppe", "team.gamma@fritzwinter.de", 0),
        ("Fire Alarm System", "Virtual team for BSB/BMT qualified employees", "feuermeldeanl@fritzwinter.de", 1),
    ]
    
    for name, description, email, is_virtual in teams:
        cursor.execute("""
            INSERT OR IGNORE INTO Teams (Name, Description, Email, IsVirtual)
            VALUES (?, ?, ?, ?)
        """, (name, description, email, is_virtual))
    
    conn.commit()
    conn.close()
    print("✅ Sample teams initialized (no springer team - springers are employee attributes)")


def initialize_sample_employees(db_path: str = "dienstplan.db"):
    """
    Initialize sample employees.
    
    Rules:
    - Team members NEVER have special functions (BSB/MBT)
    - Each team has exactly 1 Springer (backup worker)
    - Non-team members have special functions but are NEVER Springer
    - Total: 17 employees (3 teams × 5 employees + 2 non-team with special functions)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Sample employees data
    # Format: (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion, 
    #          IsSpringer, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, TeamId)
    employees = [
        # Team Alpha (TeamId=1) - 5 employees, 1 Springer
        ("Max", "Müller", "PN001", "max.mueller@fritzwinter.de", "1985-03-15", "Techniker", 0, 0, 0, 0, 1),
        ("Anna", "Schmidt", "PN002", "anna.schmidt@fritzwinter.de", "1990-07-22", "Techniker", 0, 0, 0, 0, 1),
        ("Peter", "Weber", "PN003", "peter.weber@fritzwinter.de", "1988-11-03", "Techniker", 0, 0, 0, 0, 1),
        ("Lisa", "Meyer", "PN004", "lisa.meyer@fritzwinter.de", "1992-05-18", "Techniker", 0, 0, 0, 0, 1),
        ("Robert", "Franke", "S001", "robert.franke@fritzwinter.de", "1985-05-08", "Springer", 1, 0, 0, 0, 1),
        
        # Team Beta (TeamId=2) - 5 employees, 1 Springer
        ("Julia", "Becker", "PN006", "julia.becker@fritzwinter.de", "1991-01-10", "Techniker", 0, 0, 0, 0, 2),
        ("Michael", "Schulz", "PN007", "michael.schulz@fritzwinter.de", "1986-06-14", "Techniker", 0, 0, 0, 0, 2),
        ("Sarah", "Hoffmann", "PN008", "sarah.hoffmann@fritzwinter.de", "1989-12-08", "Techniker", 0, 0, 0, 0, 2),
        ("Daniel", "Koch", "PN009", "daniel.koch@fritzwinter.de", "1993-04-25", "Techniker", 0, 0, 0, 0, 2),
        ("Thomas", "Zimmermann", "S002", "thomas.zimmermann@fritzwinter.de", "1986-12-11", "Springer", 1, 0, 0, 0, 2),
        
        # Team Gamma (TeamId=3) - 5 employees, 1 Springer
        ("Markus", "Richter", "PN011", "markus.richter@fritzwinter.de", "1984-02-20", "Techniker", 0, 0, 0, 0, 3),
        ("Stefanie", "Klein", "PN012", "stefanie.klein@fritzwinter.de", "1992-10-05", "Techniker", 0, 0, 0, 0, 3),
        ("Andreas", "Wolf", "PN013", "andreas.wolf@fritzwinter.de", "1988-07-12", "Techniker", 0, 0, 0, 0, 3),
        ("Nicole", "Schröder", "PN014", "nicole.schroeder@fritzwinter.de", "1991-03-29", "Techniker", 0, 0, 0, 0, 3),
        ("Maria", "Lange", "S003", "maria.lange@fritzwinter.de", "1990-09-24", "Springer", 1, 0, 0, 0, 3),
        
        # Non-team employees with special functions (2 employees)
        # These have special functions (BSB/MBT) but are NEVER Springers
        ("Laura", "Bauer", "SF001", "laura.bauer@fritzwinter.de", "1990-08-17", "Brandschutzbeauftragter", 0, 0, 0, 1, None),
        ("Christian", "Neumann", "SF002", "christian.neumann@fritzwinter.de", "1987-11-16", "Brandmeldetechniker", 0, 0, 1, 0, None),
    ]
    
    for vorname, name, personalnummer, email, geburtsdatum, funktion, is_springer, is_ferienjobber, is_bmt, is_bsb, team_id in employees:
        cursor.execute("""
            INSERT OR IGNORE INTO Employees 
            (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion, 
             IsSpringer, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter, TeamId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vorname, name, personalnummer, email, geburtsdatum, funktion, 
              is_springer, is_ferienjobber, is_bmt, is_bsb, team_id))
    
    conn.commit()
    conn.close()
    print("✅ Sample employees initialized: 17 total (3 teams × 5 + 2 with special functions)")


def initialize_database(db_path: str = "dienstplan.db", with_sample_data: bool = True):
    """
    Initialize complete database with schema and optional sample data.
    
    Args:
        db_path: Path to SQLite database file
        with_sample_data: Whether to include sample data
    """
    print(f"🔧 Initializing database: {db_path}")
    print("=" * 60)
    
    # Create schema
    create_database_schema(db_path)
    
    # Initialize roles
    initialize_default_roles(db_path)
    
    # Create default admin
    create_default_admin(db_path)
    
    # Initialize shift types
    initialize_shift_types(db_path)
    
    if with_sample_data:
        # Initialize sample teams
        initialize_sample_teams(db_path)
        # Initialize sample employees
        initialize_sample_employees(db_path)
    
    print("=" * 60)
    print("✅ Database initialization complete!")
    print()
    print("You can now start the server with:")
    print(f"  python main.py serve --db {db_path}")
    print()
    print("Default login credentials:")
    print("  Email: admin@fritzwinter.de")
    print("  Password: Admin123!")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize Dienstplan database')
    parser.add_argument('db_path', nargs='?', default='dienstplan.db', 
                       help='Path to database file (default: dienstplan.db)')
    parser.add_argument('--with-sample-data', '--sample-data', action='store_true',
                       help='Include sample data (teams and employees)')
    
    args = parser.parse_args()
    
    initialize_database(args.db_path, with_sample_data=args.with_sample_data)
