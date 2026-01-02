"""
Migration script to add EmployeeId column to AspNetUsers table.
This enables linking user accounts to employee records.
"""

import sqlite3
import sys


def migrate_add_employee_link(db_path: str = "dienstplan.db"):
    """
    Add EmployeeId column to AspNetUsers table to link users with employees.
    
    Args:
        db_path: Path to SQLite database
    """
    print(f"🔧 Starting migration: Add EmployeeId to AspNetUsers")
    print(f"Database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(AspNetUsers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'EmployeeId' in columns:
            print("⚠️  EmployeeId column already exists in AspNetUsers")
            print("Migration not needed.")
            return
        
        # Add EmployeeId column
        print("Adding EmployeeId column to AspNetUsers...")
        cursor.execute("""
            ALTER TABLE AspNetUsers 
            ADD COLUMN EmployeeId INTEGER REFERENCES Employees(Id)
        """)
        
        # Create index for performance
        print("Creating index on EmployeeId...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aspnetusers_employeeid 
            ON AspNetUsers(EmployeeId)
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print()
        print("The EmployeeId column has been added to AspNetUsers table.")
        print("You can now link user accounts to employee records.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()
    
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate database to add EmployeeId link to users'
    )
    parser.add_argument(
        'db_path', 
        nargs='?', 
        default='dienstplan.db',
        help='Path to database file (default: dienstplan.db)'
    )
    
    args = parser.parse_args()
    migrate_add_employee_link(args.db_path)
