"""
Database migration: Add ShiftPlanApprovals table.

This migration adds support for tracking approval status of monthly shift plans.
Administrators must approve shift plans before they become visible to regular users.
"""

import sqlite3
import sys
from datetime import datetime


def migrate(db_path: str = "dienstplan.db"):
    """
    Add ShiftPlanApprovals table to track monthly plan approval status.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Starting migration: Add ShiftPlanApprovals table to {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ShiftPlanApprovals'
        """)
        
        if cursor.fetchone():
            print("ShiftPlanApprovals table already exists. Skipping migration.")
            conn.close()
            return
        
        # Create ShiftPlanApprovals table
        cursor.execute("""
            CREATE TABLE ShiftPlanApprovals (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Year INTEGER NOT NULL,
                Month INTEGER NOT NULL,
                IsApproved INTEGER NOT NULL DEFAULT 0,
                ApprovedAt TEXT,
                ApprovedBy INTEGER,
                ApprovedByName TEXT,
                Notes TEXT,
                CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(Year, Month),
                FOREIGN KEY (ApprovedBy) REFERENCES Employees(Id)
            )
        """)
        
        print("✓ Created ShiftPlanApprovals table")
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX idx_shiftplanapprovals_year_month 
            ON ShiftPlanApprovals(Year, Month)
        """)
        
        print("✓ Created index on Year, Month")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    migrate(db_path)
