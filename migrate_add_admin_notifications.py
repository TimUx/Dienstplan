"""
Migration script to add AdminNotifications table for minimum shift strength notifications.

This migration adds support for notifying administrators when minimum shift strength
(Mindestschichtstärke) is not met due to absences, short-term vacation, etc.
"""

import sqlite3
import sys


def migrate_database(db_path: str = "dienstplan.db"):
    """
    Add AdminNotifications table to track understaffing warnings.
    
    Args:
        db_path: Path to SQLite database
    """
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='AdminNotifications'
        """)
        
        if cursor.fetchone():
            print("✓ AdminNotifications table already exists. Skipping migration.")
            conn.close()
            return
        
        # Create AdminNotifications table
        print("Creating AdminNotifications table...")
        cursor.execute("""
            CREATE TABLE AdminNotifications (
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
        
        # Create indexes for performance
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX idx_admin_notifications_created 
            ON AdminNotifications(CreatedAt DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_admin_notifications_unread 
            ON AdminNotifications(IsRead, CreatedAt DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_admin_notifications_date 
            ON AdminNotifications(ShiftDate)
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    
    # Default database path
    db_path = "dienstplan.db"
    
    # Allow override from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"✗ Database not found: {db_path}", file=sys.stderr)
        print("Please initialize the database first using: python main.py init-db", file=sys.stderr)
        sys.exit(1)
    
    # Run migration
    try:
        migrate_database(db_path)
        print("\n✓ Database migration completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
