"""
Migration script to add unique constraint on ShiftAssignments(EmployeeId, Date).

This prevents double shift assignments (same employee, same day, different/same shift).
Run this on existing databases to add the constraint.

CRITICAL: This migration will FAIL if duplicate shifts already exist.
If duplicates exist, they must be cleaned up first.
"""

import sqlite3
import sys
from datetime import datetime


def find_duplicate_shifts(db_path: str = "dienstplan.db"):
    """
    Find any duplicate shift assignments in the database.
    
    Returns:
        List of tuples: (EmployeeId, Date, ShiftCount)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT EmployeeId, Date, COUNT(*) as ShiftCount
        FROM ShiftAssignments
        GROUP BY EmployeeId, Date
        HAVING COUNT(*) > 1
        ORDER BY Date, EmployeeId
    """)
    
    duplicates = cursor.fetchall()
    conn.close()
    
    return duplicates


def remove_duplicate_shifts(db_path: str = "dienstplan.db", keep_strategy: str = "first"):
    """
    Remove duplicate shift assignments, keeping only one per employee per day.
    
    Args:
        db_path: Path to database
        keep_strategy: Which shift to keep - "first" (earliest Id), "last" (latest Id), 
                      or "manual" (requires manual cleanup)
    
    Returns:
        Number of shifts removed
    """
    if keep_strategy == "manual":
        print("Manual cleanup required. Please remove duplicates manually before migration.")
        return 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find all duplicate groups
    cursor.execute("""
        SELECT EmployeeId, Date
        FROM ShiftAssignments
        GROUP BY EmployeeId, Date
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    removed_count = 0
    
    for emp_id, date in duplicates:
        # Get all shift IDs for this employee/date
        cursor.execute("""
            SELECT Id, ShiftTypeId, IsManual, IsFixed, CreatedAt
            FROM ShiftAssignments
            WHERE EmployeeId = ? AND Date = ?
            ORDER BY Id
        """, (emp_id, date))
        
        shifts = cursor.fetchall()
        
        if keep_strategy == "first":
            # Keep the first (oldest) shift
            keep_id = shifts[0][0]
        elif keep_strategy == "last":
            # Keep the last (newest) shift
            keep_id = shifts[-1][0]
        else:
            raise ValueError(f"Unknown keep_strategy: {keep_strategy}")
        
        # Delete all except the one we're keeping
        for shift in shifts:
            shift_id = shift[0]
            if shift_id != keep_id:
                cursor.execute("DELETE FROM ShiftAssignments WHERE Id = ?", (shift_id,))
                removed_count += 1
                print(f"  Removed duplicate: EmployeeId={emp_id}, Date={date}, Id={shift_id}")
    
    conn.commit()
    conn.close()
    
    return removed_count


def add_unique_constraint(db_path: str = "dienstplan.db"):
    """
    Add unique constraint to prevent duplicate shift assignments.
    
    This will fail if duplicates exist - clean them up first!
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add unique index
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shiftassignments_unique_employee_date
            ON ShiftAssignments(EmployeeId, Date)
        """)
        
        conn.commit()
        print("[OK] Unique constraint added successfully")
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"[ERROR] Cannot add unique constraint - duplicate shifts exist!")
        print(f"        {e}")
        print(f"        Run with --clean-duplicates first to remove them.")
        return False
    
    finally:
        conn.close()


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Add unique constraint to ShiftAssignments")
    parser.add_argument("--db", default="dienstplan.db", help="Database path")
    parser.add_argument("--clean-duplicates", action="store_true", 
                       help="Remove duplicate shifts before adding constraint")
    parser.add_argument("--keep", choices=["first", "last"], default="first",
                       help="Which duplicate to keep (default: first)")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Migration: Add Unique Constraint to ShiftAssignments")
    print("=" * 70)
    print(f"Database: {args.db}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check for duplicates
    print("[1/3] Checking for duplicate shift assignments...")
    duplicates = find_duplicate_shifts(args.db)
    
    if duplicates:
        print(f"[!] Found {len(duplicates)} employees with duplicate shifts:")
        for emp_id, date, count in duplicates[:10]:  # Show first 10
            print(f"    - EmployeeId {emp_id} on {date}: {count} shifts")
        if len(duplicates) > 10:
            print(f"    ... and {len(duplicates) - 10} more")
        print()
        
        if args.clean_duplicates:
            # Step 2: Clean duplicates
            print(f"[2/3] Removing duplicate shifts (keeping {args.keep})...")
            removed = remove_duplicate_shifts(args.db, args.keep)
            print(f"[OK] Removed {removed} duplicate shift assignments")
            print()
        else:
            print("[!] Duplicates found but --clean-duplicates not specified")
            print("    Migration cannot proceed with duplicates present.")
            print("    Run with --clean-duplicates to automatically remove them,")
            print("    or clean them up manually first.")
            print()
            return 1
    else:
        print("[OK] No duplicate shifts found")
        print()
    
    # Step 3: Add constraint
    print("[3/3] Adding unique constraint...")
    success = add_unique_constraint(args.db)
    
    if success:
        print()
        print("=" * 70)
        print("[OK] Migration completed successfully!")
        print("=" * 70)
        print()
        print("The database now enforces: One shift per employee per day")
        print("Future attempts to insert duplicate shifts will be rejected.")
        return 0
    else:
        print()
        print("=" * 70)
        print("[ERROR] Migration failed!")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
