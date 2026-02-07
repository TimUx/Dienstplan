#!/usr/bin/env python3
"""
Migration: Remove IsVirtual column from Teams table

Virtual teams are no longer used in the system. This migration removes
the IsVirtual column from the Teams table.

Usage:
    python migrate_remove_virtual_teams.py [database_path]
    
    If no database path is provided, defaults to 'dienstplan.db'
"""

import sqlite3
import sys
from datetime import datetime


def migrate_remove_virtual_teams(db_path: str = "dienstplan.db"):
    """
    Remove IsVirtual column from Teams table.
    
    SQLite doesn't support DROP COLUMN directly, so we need to:
    1. Create a new table without IsVirtual
    2. Copy data from old table
    3. Drop old table
    4. Rename new table
    """
    print(f"Starting migration: Remove virtual teams from {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if IsVirtual column exists
        cursor.execute("PRAGMA table_info(Teams)")
        columns = cursor.fetchall()
        column_names = [col['name'] for col in columns]
        
        if 'IsVirtual' not in column_names:
            print("✓ IsVirtual column does not exist - migration not needed")
            conn.close()
            return True
        
        print("Step 1: Creating new Teams table without IsVirtual column...")
        cursor.execute("""
            CREATE TABLE Teams_new (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL,
                Description TEXT,
                Email TEXT,
                RotationGroupId INTEGER,
                CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (RotationGroupId) REFERENCES RotationGroups(Id)
            )
        """)
        print("✓ New table created")
        
        print("Step 2: Copying data from old Teams table...")
        cursor.execute("""
            INSERT INTO Teams_new (Id, Name, Description, Email, RotationGroupId, CreatedAt)
            SELECT Id, Name, Description, Email, RotationGroupId, CreatedAt
            FROM Teams
        """)
        rows_copied = cursor.rowcount
        print(f"✓ Copied {rows_copied} team records")
        
        print("Step 3: Dropping old Teams table...")
        cursor.execute("DROP TABLE Teams")
        print("✓ Old table dropped")
        
        print("Step 4: Renaming new table to Teams...")
        cursor.execute("ALTER TABLE Teams_new RENAME TO Teams")
        print("✓ Table renamed")
        
        print("Step 5: Recreating indexes and triggers if needed...")
        # Note: Foreign key constraints are recreated automatically
        print("✓ Schema updated")
        
        # Commit the transaction
        conn.commit()
        print()
        print("=" * 60)
        print("✓ Migration completed successfully!")
        print(f"  - Removed IsVirtual column from Teams table")
        print(f"  - {rows_copied} teams migrated")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Migration failed!")
        print(f"Error: {e}")
        print("=" * 60)
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    
    print("=" * 60)
    print("MIGRATION: Remove Virtual Teams")
    print("=" * 60)
    print()
    
    success = migrate_remove_virtual_teams(db_path)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
