"""
Migration script to add staffing requirement columns to ShiftTypes table.

This migration adds columns for minimum and maximum staffing requirements
for both weekdays and weekends to the ShiftTypes table.
"""

import sqlite3
import sys


def migrate(db_path: str = "dienstplan.db"):
    """
    Add staffing requirement columns to ShiftTypes table.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Starting migration: Adding staffing requirements to ShiftTypes table...")
    print(f"Database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ShiftTypes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        columns_to_add = []
        
        if 'MinStaffWeekday' not in columns:
            columns_to_add.append(('MinStaffWeekday', 'INTEGER NOT NULL DEFAULT 3'))
        
        if 'MaxStaffWeekday' not in columns:
            columns_to_add.append(('MaxStaffWeekday', 'INTEGER NOT NULL DEFAULT 5'))
        
        if 'MinStaffWeekend' not in columns:
            columns_to_add.append(('MinStaffWeekend', 'INTEGER NOT NULL DEFAULT 2'))
        
        if 'MaxStaffWeekend' not in columns:
            columns_to_add.append(('MaxStaffWeekend', 'INTEGER NOT NULL DEFAULT 3'))
        
        if not columns_to_add:
            print("✓ All staffing requirement columns already exist. No migration needed.")
            conn.close()
            return
        
        # Add columns
        for column_name, column_def in columns_to_add:
            print(f"  Adding column: {column_name}...")
            cursor.execute(f"ALTER TABLE ShiftTypes ADD COLUMN {column_name} {column_def}")
        
        # Set default values based on historical hardcoded values
        print("  Setting default values for existing shift types...")
        
        # Update F (Früh) shift: Weekday 4-5, Weekend 2-3
        cursor.execute("""
            UPDATE ShiftTypes 
            SET MinStaffWeekday = 4, MaxStaffWeekday = 5,
                MinStaffWeekend = 2, MaxStaffWeekend = 3
            WHERE Code = 'F'
        """)
        
        # Update S (Spät) shift: Weekday 3-4, Weekend 2-3
        cursor.execute("""
            UPDATE ShiftTypes 
            SET MinStaffWeekday = 3, MaxStaffWeekday = 4,
                MinStaffWeekend = 2, MaxStaffWeekend = 3
            WHERE Code = 'S'
        """)
        
        # Update N (Nacht) shift: Weekday 3-3, Weekend 2-3
        cursor.execute("""
            UPDATE ShiftTypes 
            SET MinStaffWeekday = 3, MaxStaffWeekday = 3,
                MinStaffWeekend = 2, MaxStaffWeekend = 3
            WHERE Code = 'N'
        """)
        
        # For other shift types (TD, ZD, etc.), use default values (already set by DEFAULT)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print(f"  Added {len(columns_to_add)} column(s) to ShiftTypes table")
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    migrate(db_path)
