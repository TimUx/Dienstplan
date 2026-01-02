"""
Migration script to add team leader support to existing databases.
This adds:
1. IsTeamLeader column to Employees table

Run this script once on existing databases.
"""

import sqlite3
import sys


def migrate_database(db_path: str = "dienstplan.db"):
    """Add team leader support to existing database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Add IsTeamLeader column to Employees table if it doesn't exist
        cursor.execute("PRAGMA table_info(Employees)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'IsTeamLeader' not in columns:
            print("  - Adding IsTeamLeader column to Employees table...")
            cursor.execute("""
                ALTER TABLE Employees 
                ADD COLUMN IsTeamLeader INTEGER NOT NULL DEFAULT 0
            """)
            print("    ✅ IsTeamLeader column added")
        else:
            print("  - IsTeamLeader column already exists")
        
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
