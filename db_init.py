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
    
    # Employees table (unified with user authentication)
    # This table combines employee data AND user authentication
    # Every employee IS a user with login credentials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Employees (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT NOT NULL UNIQUE,
            Email TEXT UNIQUE,
            NormalizedEmail TEXT,
            PasswordHash TEXT,
            SecurityStamp TEXT,
            LockoutEnd TEXT,
            AccessFailedCount INTEGER NOT NULL DEFAULT 0,
            Geburtsdatum TEXT,
            Funktion TEXT,
            IsSpringer INTEGER NOT NULL DEFAULT 0,
            IsFerienjobber INTEGER NOT NULL DEFAULT 0,
            IsBrandmeldetechniker INTEGER NOT NULL DEFAULT 0,
            IsBrandschutzbeauftragter INTEGER NOT NULL DEFAULT 0,
            IsTdQualified INTEGER NOT NULL DEFAULT 0,
            IsTeamLeader INTEGER NOT NULL DEFAULT 0,
            IsActive INTEGER NOT NULL DEFAULT 1,
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
            IsActive INTEGER NOT NULL DEFAULT 1,
            WorksMonday INTEGER NOT NULL DEFAULT 1,
            WorksTuesday INTEGER NOT NULL DEFAULT 1,
            WorksWednesday INTEGER NOT NULL DEFAULT 1,
            WorksThursday INTEGER NOT NULL DEFAULT 1,
            WorksFriday INTEGER NOT NULL DEFAULT 1,
            WorksSaturday INTEGER NOT NULL DEFAULT 0,
            WorksSunday INTEGER NOT NULL DEFAULT 0,
            WeeklyWorkingHours REAL NOT NULL DEFAULT 40.0,
            MinStaffWeekday INTEGER NOT NULL DEFAULT 3,
            MaxStaffWeekday INTEGER NOT NULL DEFAULT 5,
            MinStaffWeekend INTEGER NOT NULL DEFAULT 2,
            MaxStaffWeekend INTEGER NOT NULL DEFAULT 3,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ModifiedAt TEXT,
            CreatedBy TEXT,
            ModifiedBy TEXT
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
    
    # AbsenceTypes table for custom absence type definitions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AbsenceTypes (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Code TEXT NOT NULL UNIQUE,
            ColorCode TEXT NOT NULL DEFAULT '#E0E0E0',
            IsSystemType INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)
    
    # Absences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Absences (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            Type INTEGER NOT NULL,
            AbsenceTypeId INTEGER,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Notes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (AbsenceTypeId) REFERENCES AbsenceTypes(Id)
        )
    """)
    
    # AspNetUsers table - DEPRECATED
    # This table is no longer used. Authentication is now part of Employees table.
    # Kept for backwards compatibility during migration only.
    # Will be removed in future versions.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AspNetUsers (
            Id TEXT PRIMARY KEY,
            Email TEXT NOT NULL UNIQUE,
            NormalizedEmail TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL,
            SecurityStamp TEXT NOT NULL,
            FullName TEXT,
            EmployeeId INTEGER,
            LockoutEnd TEXT,
            AccessFailedCount INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
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
    
    # AspNetUserRoles table (maps Employees to Roles)
    # Note: UserId column actually contains EmployeeId after migration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AspNetUserRoles (
            UserId TEXT NOT NULL,
            RoleId TEXT NOT NULL,
            PRIMARY KEY (UserId, RoleId),
            FOREIGN KEY (UserId) REFERENCES Employees(Id),
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
    
    # VacationPeriods table (Ferienzeiten)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VacationPeriods (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            ColorCode TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)
    
    # VacationYearApprovals table (for year-level vacation plan approval)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VacationYearApprovals (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Year INTEGER NOT NULL UNIQUE,
            IsApproved INTEGER NOT NULL DEFAULT 0,
            ApprovedAt TEXT,
            ApprovedBy TEXT,
            Notes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ModifiedAt TEXT
        )
    """)
    
    # TeamShiftAssignments table (many-to-many: which teams can work which shifts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamShiftAssignments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            TeamId INTEGER NOT NULL,
            ShiftTypeId INTEGER NOT NULL,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            FOREIGN KEY (TeamId) REFERENCES Teams(Id) ON DELETE CASCADE,
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
            UNIQUE(TeamId, ShiftTypeId)
        )
    """)
    
    # ShiftTypeRelationships table (defines which shifts are related and their order)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ShiftTypeRelationships (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ShiftTypeId INTEGER NOT NULL,
            RelatedShiftTypeId INTEGER NOT NULL,
            DisplayOrder INTEGER NOT NULL,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CreatedBy TEXT,
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
            FOREIGN KEY (RelatedShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
            UNIQUE(ShiftTypeId, RelatedShiftTypeId)
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
    
    # AdminNotifications table (for minimum shift strength alerts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AdminNotifications (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Type TEXT NOT NULL,
            Severity TEXT NOT NULL DEFAULT 'WARNING',
            Title TEXT NOT NULL,
            Message TEXT NOT NULL,
            ShiftDate TEXT,
            ShiftCode TEXT,
            TeamId INTEGER,
            EmployeeId INTEGER,
            AbsenceId INTEGER,
            RequiredStaff INTEGER,
            ActualStaff INTEGER,
            IsRead INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ReadAt TEXT,
            ReadBy TEXT,
            FOREIGN KEY (TeamId) REFERENCES Teams(Id),
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (AbsenceId) REFERENCES Absences(Id)
        )
    """)
    
    # ShiftPlanApprovals table (for monthly shift plan approval)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ShiftPlanApprovals (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Year INTEGER NOT NULL,
            Month INTEGER NOT NULL,
            IsApproved INTEGER NOT NULL DEFAULT 0,
            ApprovedAt TEXT,
            ApprovedBy INTEGER,
            ApprovedByName TEXT,
            Notes TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(Year, Month),
            FOREIGN KEY (ApprovedBy) REFERENCES Employees(Id)
        )
    """)
    
    # GlobalSettings table (for shift planning configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GlobalSettings (
            Id INTEGER PRIMARY KEY CHECK (Id = 1),
            MaxConsecutiveShifts INTEGER NOT NULL DEFAULT 6,
            MaxConsecutiveNightShifts INTEGER NOT NULL DEFAULT 3,
            MinRestHoursBetweenShifts INTEGER NOT NULL DEFAULT 11,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)
    
    # Initialize default global settings if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO GlobalSettings (Id, MaxConsecutiveShifts, MaxConsecutiveNightShifts, MinRestHoursBetweenShifts)
        VALUES (1, 6, 3, 11)
    """)
    
    # EmailSettings table (for SMTP configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EmailSettings (
            Id INTEGER PRIMARY KEY CHECK (Id = 1),
            SmtpHost TEXT,
            SmtpPort INTEGER DEFAULT 587,
            UseSsl INTEGER NOT NULL DEFAULT 1,
            RequiresAuthentication INTEGER NOT NULL DEFAULT 1,
            Username TEXT,
            Password TEXT,
            SenderEmail TEXT,
            SenderName TEXT,
            ReplyToEmail TEXT,
            IsEnabled INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)
    
    # PasswordResetTokens table (for password reset flow)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PasswordResetTokens (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            Token TEXT NOT NULL UNIQUE,
            ExpiresAt TEXT NOT NULL,
            IsUsed INTEGER NOT NULL DEFAULT 0,
            UsedAt TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
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
        CREATE INDEX IF NOT EXISTS idx_absences_type 
        ON Absences(AbsenceTypeId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditlogs_timestamp 
        ON AuditLogs(Timestamp DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditlogs_entity 
        ON AuditLogs(EntityName, EntityId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vacationperiods_dates 
        ON VacationPeriods(StartDate, EndDate)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_aspnetusers_employeeid 
        ON AspNetUsers(EmployeeId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_admin_notifications_created 
        ON AdminNotifications(CreatedAt DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shiftplanapprovals_year_month 
        ON ShiftPlanApprovals(Year, Month)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_admin_notifications_unread 
        ON AdminNotifications(IsRead, CreatedAt DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_admin_notifications_date 
        ON AdminNotifications(ShiftDate)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_teamshiftassignments_team 
        ON TeamShiftAssignments(TeamId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_teamshiftassignments_shift 
        ON TeamShiftAssignments(ShiftTypeId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shifttyperelationships_shift 
        ON ShiftTypeRelationships(ShiftTypeId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_passwordresettokens_token 
        ON PasswordResetTokens(Token)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_passwordresettokens_employee 
        ON PasswordResetTokens(EmployeeId, IsUsed, ExpiresAt)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Database schema created successfully: {db_path}")


def initialize_default_roles(db_path: str = "dienstplan.db"):
    """Initialize default roles (Admin, Mitarbeiter)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    roles = [
        ("admin-role-id", "Admin", "ADMIN"),
        ("mitarbeiter-role-id", "Mitarbeiter", "MITARBEITER")
    ]
    
    for role_id, name, normalized in roles:
        cursor.execute("""
            INSERT OR IGNORE INTO AspNetRoles (Id, Name, NormalizedName)
            VALUES (?, ?, ?)
        """, (role_id, name, normalized))
    
    conn.commit()
    conn.close()
    print("[OK] Default roles initialized (Admin, Mitarbeiter)")


def hash_password(password: str) -> str:
    """
    Simple password hashing using SHA256.
    
    Note: This matches the web_api.py implementation for consistency.
    For production, consider upgrading to bcrypt, scrypt, or Argon2.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def create_default_admin(db_path: str = "dienstplan.db"):
    """Create default admin employee with login credentials"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    admin_email = "admin@fritzwinter.de"
    admin_password = "Admin123!"
    
    # Check if admin already exists (check Employees table now)
    cursor.execute("SELECT Id FROM Employees WHERE Email = ?", (admin_email,))
    existing_admin = cursor.fetchone()
    
    if existing_admin:
        print("[!] Admin employee already exists")
        admin_id = existing_admin[0]
    else:
        # Create admin employee with authentication credentials
        password_hash = hash_password(admin_password)
        security_stamp = secrets.token_hex(16)
        
        cursor.execute("""
            INSERT INTO Employees 
            (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash, SecurityStamp,
             Funktion, IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter,
             IsTdQualified, IsTeamLeader, TeamId, AccessFailedCount, IsActive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, NULL, 0, 1)
        """, (
            "Admin",  # Vorname
            "Administrator",  # Name
            "ADMIN001",  # Personalnummer
            admin_email,
            admin_email.upper(),
            password_hash,
            security_stamp,
            "Administrator"  # Funktion
        ))
        
        admin_id = cursor.lastrowid
        print(f"[OK] Default admin employee created (ID: {admin_id})")
    
    # Assign Admin role (UserId in AspNetUserRoles now refers to Employee Id)
    cursor.execute("""
        INSERT OR IGNORE INTO AspNetUserRoles (UserId, RoleId)
        VALUES (?, ?)
    """, (str(admin_id), "admin-role-id"))
    
    conn.commit()
    conn.close()
    
    print(f"   Email: {admin_email}")
    print(f"   Password: {admin_password}")
    print(f"   [!] CHANGE THIS PASSWORD AFTER FIRST LOGIN!")


def initialize_shift_types(db_path: str = "dienstplan.db"):
    """
    Initialize standard shift types.
    
    The three main shifts are created in rotation order: Früh → Nacht → Spät.
    Additional shifts can be created manually as needed.
    
    Official absence codes (U, AU, L) are stored in Absences table,
    NOT as shift types. Shift types are only for actual work shifts.
    
    All three shifts are configured to work Monday-Sunday (all 7 days).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Format: (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode, WeeklyWorkingHours, 
    #          MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend,
    #          WorksMonday, WorksTuesday, WorksWednesday, WorksThursday, WorksFriday, WorksSaturday, WorksSunday)
    # All three shifts work Monday-Sunday (all 7 days) - represented by 1 for each day
    # Note: IDs are assigned based on legacy system compatibility (F=1, S=2, N=3), not rotation order
    # The rotation order F→N→S is defined separately in initialize_shift_type_relationships()
    # 
    # IMPORTANT: Max staffing set to 10 to allow cross-team assignments so all employees
    # can reach their monthly minimum target hours (e.g., 192h minimum for 48h/week).
    # Employees can work MORE than minimum hours but not less.
    # With 3 teams of 5 employees (15 total), max=10 accommodates flexible distribution.
    shift_types = [
        # Frühschicht: 05:45–13:45 Uhr (Mo–Fr mind. 4 Personen, max. 10)
        # Works all 7 days: Monday-Sunday
        # Max set to 10 to allow cross-team assignments and flexible hour distribution
        (1, "F", "Frühschicht", "05:45", "13:45", 8.0, "#4CAF50", 48.0, 4, 10, 2, 5, 1, 1, 1, 1, 1, 1, 1),
        # Nachtschicht: 21:45–05:45 Uhr (Mo–Fr mind. 3 Personen, max. 10)
        # Works all 7 days: Monday-Sunday
        # Max set to 10 to allow cross-team assignments and flexible hour distribution
        (3, "N", "Nachtschicht", "21:45", "05:45", 8.0, "#2196F3", 48.0, 3, 10, 2, 5, 1, 1, 1, 1, 1, 1, 1),
        # Spätschicht: 13:45–21:45 Uhr (Mo–Fr mind. 3 Personen, max. 10)
        # Works all 7 days: Monday-Sunday  
        # Max set to 10 to allow cross-team assignments and flexible hour distribution
        (2, "S", "Spätschicht", "13:45", "21:45", 8.0, "#FF9800", 48.0, 3, 10, 2, 5, 1, 1, 1, 1, 1, 1, 1),
        # Additional shifts (Z, BMT, BSB, TD) can be created manually in the UI as needed
    ]
    
    for shift_type in shift_types:
        cursor.execute("""
            INSERT OR IGNORE INTO ShiftTypes 
            (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode, WeeklyWorkingHours,
             MinStaffWeekday, MaxStaffWeekday, MinStaffWeekend, MaxStaffWeekend,
             WorksMonday, WorksTuesday, WorksWednesday, WorksThursday, WorksFriday, WorksSaturday, WorksSunday)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, shift_type)
    
    conn.commit()
    conn.close()
    print("[OK] Standard shift types initialized: Früh, Nacht, Spät (48h/week, all working Monday-Sunday)")


def initialize_shift_type_relationships(db_path: str = "dienstplan.db"):
    """
    Initialize shift type relationships to define the shift rotation order.
    
    Defines the shift sequence for the three main shifts:
    Frühschicht (F) → Nachtschicht (N) → Spätschicht (S)
    
    This means:
    - After Frühschicht (F), the next shift should be Nachtschicht (N)
    - After Nachtschicht (N), the next shift should be Spätschicht (S)
    - After Spätschicht (S), the next shift should be Frühschicht (F)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dictionary-style access
    cursor = conn.cursor()
    
    # Check if shift types exist
    cursor.execute("SELECT Id, Code FROM ShiftTypes WHERE Code IN ('F', 'N', 'S')")
    shifts = {row['Code']: row['Id'] for row in cursor.fetchall()}
    
    if len(shifts) < 3:
        missing = set(['F', 'N', 'S']) - set(shifts.keys())
        print(f"[!] Not all shift types found, skipping relationship initialization. Missing: {', '.join(missing)}")
        conn.close()
        return
    
    # Define relationships: ShiftTypeId → RelatedShiftTypeId with DisplayOrder
    # For Frühschicht (F): next shifts are Nachtschicht (1st priority), Spätschicht (2nd priority)
    # For Nachtschicht (N): next shift is Spätschicht (1st priority), Frühschicht (2nd priority)
    # For Spätschicht (S): next shift is Frühschicht (1st priority), Nachtschicht (2nd priority)
    relationships = [
        # Frühschicht → Nachtschicht (1st), Spätschicht (2nd)
        (shifts['F'], shifts['N'], 1),  # F → N (highest priority)
        (shifts['F'], shifts['S'], 2),  # F → S (second priority)
        # Nachtschicht → Spätschicht (1st), Frühschicht (2nd)
        (shifts['N'], shifts['S'], 1),  # N → S (highest priority)
        (shifts['N'], shifts['F'], 2),  # N → F (second priority)
        # Spätschicht → Frühschicht (1st), Nachtschicht (2nd)
        (shifts['S'], shifts['F'], 1),  # S → F (highest priority)
        (shifts['S'], shifts['N'], 2),  # S → N (second priority)
    ]
    
    for shift_id, related_shift_id, display_order in relationships:
        cursor.execute("""
            INSERT OR IGNORE INTO ShiftTypeRelationships 
            (ShiftTypeId, RelatedShiftTypeId, DisplayOrder, CreatedBy)
            VALUES (?, ?, ?, ?)
        """, (shift_id, related_shift_id, display_order, 'system'))
    
    conn.commit()
    conn.close()
    print("[OK] Shift type relationships initialized: F -> N -> S rotation")


def initialize_absence_types(db_path: str = "dienstplan.db"):
    """
    Initialize standard absence types (U, AU, L).
    
    These are the system absence types that must always exist.
    Custom absence types can be added later via the Admin interface.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if absence types already exist
    cursor.execute("SELECT COUNT(*) FROM AbsenceTypes WHERE IsSystemType = 1")
    count = cursor.fetchone()[0]
    
    if count >= 3:
        print("[!] Standard absence types already initialized")
        conn.close()
        return
    
    # Standard absence types
    # Format: (Name, Code, ColorCode, IsSystemType)
    standard_types = [
        ('Urlaub', 'U', '#90EE90', 1),  # Light green for vacation
        ('Krank / AU', 'AU', '#FFB6C1', 1),  # Light pink for sick leave
        ('Lehrgang', 'L', '#87CEEB', 1)  # Sky blue for training
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO AbsenceTypes (Name, Code, ColorCode, IsSystemType, CreatedBy)
        VALUES (?, ?, ?, ?, 'system')
    """, standard_types)
    
    conn.commit()
    conn.close()
    print("[OK] Standard absence types initialized (U, AU, L)")


def initialize_sample_teams(db_path: str = "dienstplan.db"):
    """
    Initialize sample teams.
    
    Note: Team IDs are explicitly set.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Sample teams with explicit IDs
    # Format: (Id, Name, Description, Email, IsVirtual)
    teams = [
        (1, "Team Alpha", "Erste Schichtgruppe", "team.alpha@fritzwinter.de", 0),
        (2, "Team Beta", "Zweite Schichtgruppe", "team.beta@fritzwinter.de", 0),
        (3, "Team Gamma", "Dritte Schichtgruppe", "team.gamma@fritzwinter.de", 0),
    ]
    
    for team_id, name, description, email, is_virtual in teams:
        cursor.execute("""
            INSERT OR IGNORE INTO Teams (Id, Name, Description, Email, IsVirtual)
            VALUES (?, ?, ?, ?, ?)
        """, (team_id, name, description, email, is_virtual))
    
    conn.commit()
    conn.close()
    print("[OK] Sample teams initialized")


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
    print("[OK] Sample employees initialized: 17 total (3 teams × 5 + 2 with special functions)")


def initialize_database(db_path: str = "dienstplan.db", with_sample_data: bool = True):
    """
    Initialize complete database with schema and optional sample data.
    
    Args:
        db_path: Path to SQLite database file
        with_sample_data: Whether to include sample data
    """
    print(f"[*] Initializing database: {db_path}")
    print("=" * 60)
    
    # Create schema
    create_database_schema(db_path)
    
    # Initialize roles
    initialize_default_roles(db_path)
    
    # Create default admin
    create_default_admin(db_path)
    
    # Initialize shift types
    initialize_shift_types(db_path)
    
    # Initialize shift type relationships (rotation order: F → N → S)
    initialize_shift_type_relationships(db_path)
    
    # Initialize standard absence types (U, AU, L)
    initialize_absence_types(db_path)
    
    if with_sample_data:
        # Initialize sample teams
        initialize_sample_teams(db_path)
        # Initialize sample employees
        initialize_sample_employees(db_path)
    
    print("=" * 60)
    print("[OK] Database initialization complete!")
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
