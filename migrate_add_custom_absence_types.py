#!/usr/bin/env python3
"""
Migration script to add custom absence types feature to existing Dienstplan databases.

This script adds:
- AbsenceTypes table for defining custom absence types with color codes
- Migrates existing absences to use the new system

Usage:
    python migrate_add_custom_absence_types.py [database_path]
    
    If no database path is provided, defaults to 'dienstplan.db'
"""

import sqlite3
import sys
import os


def migrate_database(db_path: str = "dienstplan.db"):
    """
    Add custom absence types tables to existing database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return False
    
    print(f"Migrating database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if AbsenceTypes table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AbsenceTypes'")
        if cursor.fetchone():
            print("⚠️  AbsenceTypes table already exists, skipping...")
        else:
            print("Creating AbsenceTypes table...")
            cursor.execute("""
                CREATE TABLE AbsenceTypes (
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
            print("✓ AbsenceTypes table created")
            
            # Insert standard absence types (U, AU, L)
            print("Inserting standard absence types (U, AU, L)...")
            standard_types = [
                ('Urlaub', 'U', '#90EE90', 1),  # Light green for vacation
                ('Krank / AU', 'AU', '#FFB6C1', 1),  # Light pink for sick leave
                ('Lehrgang', 'L', '#87CEEB', 1)  # Sky blue for training
            ]
            
            cursor.executemany("""
                INSERT INTO AbsenceTypes (Name, Code, ColorCode, IsSystemType)
                VALUES (?, ?, ?, ?)
            """, standard_types)
            print("✓ Standard absence types inserted")
        
        # Check if Absences table has AbsenceTypeId column
        cursor.execute("PRAGMA table_info(Absences)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'AbsenceTypeId' not in columns:
            print("Adding AbsenceTypeId column to Absences table...")
            
            # Add the new column
            cursor.execute("""
                ALTER TABLE Absences ADD COLUMN AbsenceTypeId INTEGER
            """)
            
            # Migrate existing absences to use AbsenceTypeId
            print("Migrating existing absences to use AbsenceTypeId...")
            cursor.execute("""
                UPDATE Absences 
                SET AbsenceTypeId = (
                    SELECT Id FROM AbsenceTypes 
                    WHERE (AbsenceTypes.Code = 'U' AND Absences.Type = 2)
                       OR (AbsenceTypes.Code = 'AU' AND Absences.Type = 1)
                       OR (AbsenceTypes.Code = 'L' AND Absences.Type = 3)
                )
            """)
            
            # Verify migration
            cursor.execute("SELECT COUNT(*) FROM Absences WHERE AbsenceTypeId IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                print(f"⚠️  Warning: {null_count} absences could not be migrated automatically")
                print(f"   Action required: These absences have invalid Type values")
                print(f"   Recommendation: Review and correct these records manually or contact support")
            else:
                print("✓ All existing absences migrated to new system")
        else:
            print("⚠️  AbsenceTypeId column already exists in Absences table, skipping...")
        
        # Create index for AbsenceTypeId
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_absences_type 
            ON Absences(AbsenceTypeId)
        """)
        
        conn.commit()
        print("=" * 60)
        print("✓ Migration completed successfully!")
        print()
        print("Notes:")
        print("- Standard absence types (U, AU, L) have been created")
        print("- You can now create custom absence types via the Admin interface")
        print("- Old 'Type' column in Absences table is kept for backward compatibility")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
