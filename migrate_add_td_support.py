"""
Migration script to add TD (Tagdienst) support, virtual teams, and audit logs to existing databases.
This adds:
1. IsTdQualified column to Employees table
2. TD shift type to ShiftTypes table
3. IsVirtual column to Teams table
4. AuditLogs table for change tracking

Run this script once on existing databases.
"""

import sqlite3
import sys


def migrate_database(db_path: str = "dienstplan.db"):
    """Add TD support, virtual teams, and audit logs to existing database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Migrating database: {db_path}")
    
    try:
        # 1. Add IsTdQualified column to Employees table if it doesn't exist
        cursor.execute("PRAGMA table_info(Employees)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'IsTdQualified' not in columns:
            print("  - Adding IsTdQualified column to Employees table...")
            cursor.execute("""
                ALTER TABLE Employees 
                ADD COLUMN IsTdQualified INTEGER NOT NULL DEFAULT 0
            """)
            print("    ✅ IsTdQualified column added")
        else:
            print("  - IsTdQualified column already exists")
        
        # 2. Add TD shift type if it doesn't exist
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'TD'")
        if not cursor.fetchone():
            print("  - Adding TD shift type...")
            cursor.execute("""
                INSERT INTO ShiftTypes (Code, Name, StartTime, EndTime, DurationHours, ColorCode)
                VALUES ('TD', 'Tagdienst', '06:00', '16:30', 10.5, '#673AB7')
            """)
            print("    ✅ TD shift type added")
        else:
            print("  - TD shift type already exists")
        
        # 3. Add IsVirtual column to Teams table if it doesn't exist
        cursor.execute("PRAGMA table_info(Teams)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'IsVirtual' not in columns:
            print("  - Adding IsVirtual column to Teams table...")
            cursor.execute("""
                ALTER TABLE Teams 
                ADD COLUMN IsVirtual INTEGER NOT NULL DEFAULT 0
            """)
            print("    ✅ IsVirtual column added")
        else:
            print("  - IsVirtual column already exists")
        
        # 4. Create AuditLogs table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AuditLogs'")
        if not cursor.fetchone():
            print("  - Creating AuditLogs table...")
            cursor.execute("""
                CREATE TABLE AuditLogs (
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
            
            # Create indexes for AuditLogs
            cursor.execute("""
                CREATE INDEX idx_auditlogs_timestamp 
                ON AuditLogs(Timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX idx_auditlogs_entity 
                ON AuditLogs(EntityName, EntityId)
            """)
            
            print("    ✅ AuditLogs table and indexes created")
        else:
            print("  - AuditLogs table already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    migrate_database(db_path)
