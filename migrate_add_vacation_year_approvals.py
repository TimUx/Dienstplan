#!/usr/bin/env python3
"""
Migration script to add VacationYearApprovals table.
This table stores admin approval settings for displaying vacation data per year.
"""

import sqlite3
import sys
from datetime import datetime

def migrate():
    """Add VacationYearApprovals table"""
    db_path = 'data/dienstplan.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting migration: Add VacationYearApprovals table...")
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='VacationYearApprovals'
        """)
        
        if cursor.fetchone():
            print("❌ Table VacationYearApprovals already exists. Skipping migration.")
            conn.close()
            return
        
        # Create VacationYearApprovals table
        cursor.execute("""
            CREATE TABLE VacationYearApprovals (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Year INTEGER NOT NULL UNIQUE,
                IsApproved INTEGER NOT NULL DEFAULT 0,
                ApprovedAt TEXT,
                ApprovedBy TEXT,
                CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ModifiedAt TEXT,
                Notes TEXT
            )
        """)
        
        print("✓ Created VacationYearApprovals table")
        
        # Create index on Year for faster lookups
        cursor.execute("""
            CREATE INDEX idx_vacation_year_approvals_year 
            ON VacationYearApprovals(Year)
        """)
        
        print("✓ Created index on Year column")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()
