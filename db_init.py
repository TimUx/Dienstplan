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
    Note: In production, use bcrypt or Argon2.
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
    """Initialize standard shift types"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    shift_types = [
        (1, "F", "Früh", "05:45", "13:45", 8.0, "#4CAF50"),
        (2, "S", "Spät", "13:45", "21:45", 8.0, "#FF9800"),
        (3, "N", "Nacht", "21:45", "05:45", 8.0, "#2196F3"),
        (4, "Z", "Zwischendienst", "08:00", "16:00", 8.0, "#9C27B0"),
        (5, "BMT", "Brandmeldetechniker", "06:00", "14:00", 8.0, "#F44336"),
        (6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", 9.5, "#E91E63"),
        (7, "K", "Krank", "00:00", "00:00", 0.0, "#9E9E9E"),
        (8, "U", "Urlaub", "00:00", "00:00", 0.0, "#00BCD4"),
        (9, "L", "Lehrgang", "00:00", "00:00", 0.0, "#795548"),
    ]
    
    for shift_type in shift_types:
        cursor.execute("""
            INSERT OR IGNORE INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, shift_type)
    
    conn.commit()
    conn.close()
    print("✅ Standard shift types initialized")


def initialize_sample_teams(db_path: str = "dienstplan.db"):
    """Initialize sample teams"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    teams = [
        ("Team Alpha", "Erste Schichtgruppe", "team.alpha@fritzwinter.de"),
        ("Team Beta", "Zweite Schichtgruppe", "team.beta@fritzwinter.de"),
        ("Team Gamma", "Dritte Schichtgruppe", "team.gamma@fritzwinter.de"),
    ]
    
    for name, description, email in teams:
        cursor.execute("""
            INSERT OR IGNORE INTO Teams (Name, Description, Email)
            VALUES (?, ?, ?)
        """, (name, description, email))
    
    conn.commit()
    conn.close()
    print("✅ Sample teams initialized")


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
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    initialize_database(db_path, with_sample_data=True)
