#!/usr/bin/env python3
"""
Script to delete all shift assignments from the Dienstplan database.

This script will:
- Delete all entries from the ShiftAssignments table
- Optionally create a backup before deletion
- Provide confirmation before executing the deletion

Usage:
    python delete_all_shifts.py [database_path] [--no-backup] [--yes]
    
Arguments:
    database_path: Path to the SQLite database file (default: 'dienstplan.db')
    --no-backup: Skip creating a backup before deletion
    --yes: Skip confirmation prompt (use with caution!)

Examples:
    # Delete all shifts with confirmation and backup
    python delete_all_shifts.py
    
    # Delete all shifts from a specific database
    python delete_all_shifts.py /path/to/dienstplan.db
    
    # Delete without creating a backup (not recommended)
    python delete_all_shifts.py --no-backup
    
    # Delete without confirmation (automated scripts)
    python delete_all_shifts.py --yes
"""

import sqlite3
import sys
import os
import shutil
from datetime import datetime


def create_backup(db_path: str) -> str:
    """
    Create a backup of the database file.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Path to the backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created successfully")
    
    return backup_path


def delete_all_shifts(db_path: str = "dienstplan.db", create_backup_flag: bool = True, skip_confirmation: bool = False):
    """
    Delete all shift assignments from the database.
    
    Args:
        db_path: Path to the SQLite database file
        create_backup_flag: Whether to create a backup before deletion
        skip_confirmation: Whether to skip the confirmation prompt
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(db_path):
        print(f"❌ Error: Database file '{db_path}' not found!")
        return False
    
    print("=" * 70)
    print("DELETE ALL SHIFTS - Dienstplan Database Tool")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()
    
    # Connect to database to check current state
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if ShiftAssignments table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ShiftAssignments'")
        if not cursor.fetchone():
            print("❌ Error: ShiftAssignments table not found in database!")
            conn.close()
            return False
        
        # Count current shifts
        cursor.execute("SELECT COUNT(*) FROM ShiftAssignments")
        shift_count = cursor.fetchone()[0]
        
        print(f"Current number of shift assignments: {shift_count}")
        
        if shift_count == 0:
            print("ℹ️  No shifts to delete. Database is already empty.")
            conn.close()
            return True
        
        print()
        
        # Confirmation prompt
        if not skip_confirmation:
            print("⚠️  WARNING: This will permanently delete ALL shift assignments!")
            print("   This action cannot be undone (unless you have a backup).")
            print()
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            
            if response not in ['yes', 'y']:
                print("❌ Operation cancelled by user.")
                conn.close()
                return False
        
        # Create backup if requested
        if create_backup_flag:
            print()
            try:
                backup_path = create_backup(db_path)
                print(f"   You can restore from: {backup_path}")
            except Exception as e:
                print(f"❌ Error creating backup: {e}")
                print("   Aborting deletion to prevent data loss.")
                conn.close()
                return False
        
        print()
        print("Deleting all shift assignments...")
        
        # Delete all shifts using explicit transaction
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("DELETE FROM ShiftAssignments")
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM ShiftAssignments")
        remaining_count = cursor.fetchone()[0]
        
        if remaining_count == 0:
            print(f"✓ Successfully deleted {shift_count} shift assignment(s)")
            print()
            print("=" * 70)
            print("Operation completed successfully!")
            print("=" * 70)
            result = True
        else:
            print(f"⚠️  Warning: {remaining_count} shift(s) remain in database")
            result = False
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        result = False
    finally:
        if conn:
            conn.close()
    
    return result


def main():
    """Main entry point for the script"""
    # Default values
    db_path = "dienstplan.db"
    create_backup_flag = True
    skip_confirmation = False
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    for arg in args:
        if arg in ["--help", "-h"]:
            print(__doc__)
            sys.exit(0)
        elif arg == "--no-backup":
            create_backup_flag = False
        elif arg in ["--yes", "-y"]:
            skip_confirmation = True
        elif arg.startswith("--") or arg.startswith("-"):
            print(f"❌ Unknown option: {arg}")
            print()
            print(__doc__)
            sys.exit(1)
        else:
            # Assume it's a database path
            db_path = arg
    
    # Execute deletion
    success = delete_all_shifts(db_path, create_backup_flag, skip_confirmation)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
