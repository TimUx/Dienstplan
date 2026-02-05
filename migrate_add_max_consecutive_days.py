#!/usr/bin/env python3
"""
Migration Script: Add MaxConsecutiveDays to ShiftTypes

This script:
1. Adds MaxConsecutiveDays column to ShiftTypes table
2. Migrates existing GlobalSettings values to ShiftTypes:
   - Sets MaxConsecutiveDays = MaxConsecutiveShifts (default 6) for F and S shifts
   - Sets MaxConsecutiveDays = MaxConsecutiveNightShifts (default 3) for N shift
   - Sets MaxConsecutiveDays = 6 for other shift types

Run this script on existing databases to migrate to the new schema.
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str):
    """Perform the migration on the database"""
    print(f"Migrating database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if MaxConsecutiveDays column already exists
        cursor.execute("PRAGMA table_info(ShiftTypes)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'MaxConsecutiveDays' in columns:
            print("✓ MaxConsecutiveDays column already exists")
        else:
            print("Adding MaxConsecutiveDays column to ShiftTypes table...")
            cursor.execute("""
                ALTER TABLE ShiftTypes 
                ADD COLUMN MaxConsecutiveDays INTEGER NOT NULL DEFAULT 6
            """)
            print("✓ MaxConsecutiveDays column added")
        
        # Load GlobalSettings values
        cursor.execute("SELECT MaxConsecutiveShifts, MaxConsecutiveNightShifts FROM GlobalSettings WHERE Id = 1")
        global_settings = cursor.fetchone()
        
        if global_settings:
            max_consecutive_general = global_settings['MaxConsecutiveShifts']
            max_consecutive_night = global_settings['MaxConsecutiveNightShifts']
            print(f"✓ Loaded GlobalSettings: general={max_consecutive_general}, night={max_consecutive_night}")
        else:
            # Use defaults if GlobalSettings not found
            max_consecutive_general = 6
            max_consecutive_night = 3
            print(f"⚠ GlobalSettings not found, using defaults: general={max_consecutive_general}, night={max_consecutive_night}")
        
        # Update shift types with appropriate values
        print("Updating ShiftTypes with MaxConsecutiveDays values...")
        
        # Get all shift types
        cursor.execute("SELECT Id, Code, Name FROM ShiftTypes")
        shift_types = cursor.fetchall()
        
        for shift in shift_types:
            shift_id = shift['Id']
            shift_code = shift['Code']
            shift_name = shift['Name']
            
            # Determine the appropriate max consecutive days
            if shift_code == 'N':
                max_consecutive_days = max_consecutive_night
            else:
                max_consecutive_days = max_consecutive_general
            
            # Update the shift type
            cursor.execute("""
                UPDATE ShiftTypes 
                SET MaxConsecutiveDays = ? 
                WHERE Id = ?
            """, (max_consecutive_days, shift_id))
            
            print(f"  ✓ {shift_code} ({shift_name}): MaxConsecutiveDays = {max_consecutive_days}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nNote: The GlobalSettings table still contains MaxConsecutiveShifts and MaxConsecutiveNightShifts")
        print("      for backward compatibility, but they are no longer used by the algorithm.")
        print("      Each shift type now has its own MaxConsecutiveDays setting.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "dienstplan.db"
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    
    print("=" * 70)
    print("Migration: Add MaxConsecutiveDays to ShiftTypes")
    print("=" * 70)
    print()
    
    migrate_database(db_path)
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
