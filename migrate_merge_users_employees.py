"""
Migration script to merge Employees and AspNetUsers into a unified data model.

This migration:
1. Adds authentication fields to Employees table
2. Migrates existing AspNetUsers data to Employees
3. Keeps AspNetUserRoles for role management
4. Removes the separate AspNetUsers table (or marks it deprecated)

IMPORTANT: This is a breaking change. Backup your database before running!
"""

import sqlite3
import sys
import secrets
import hashlib


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def migrate_merge_users_employees(db_path: str = "dienstplan.db"):
    """
    Merge AspNetUsers and Employees tables into unified Employees table.
    
    Strategy:
    1. Add authentication fields to Employees table
    2. Migrate AspNetUsers data to Employees
    3. Update foreign keys to point to Employees
    4. Keep AspNetUserRoles but update to use EmployeeId
    
    Args:
        db_path: Path to SQLite database
    """
    print(f"🔧 Starting migration: Merge Users and Employees")
    print(f"Database: {db_path}")
    print("=" * 60)
    print("⚠️  WARNING: This is a major database migration!")
    print("⚠️  Backup your database before proceeding!")
    print("=" * 60)
    
    response = input("Continue with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Step 1: Add authentication fields to Employees table
        print("\n1. Adding authentication fields to Employees table...")
        
        auth_fields = [
            "Email TEXT UNIQUE",
            "NormalizedEmail TEXT",
            "PasswordHash TEXT",
            "SecurityStamp TEXT",
            "LockoutEnd TEXT",
            "AccessFailedCount INTEGER DEFAULT 0",
            "IsActive INTEGER DEFAULT 1"
        ]
        
        # Check which fields already exist
        cursor.execute("PRAGMA table_info(Employees)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        for field in auth_fields:
            field_name = field.split()[0]
            if field_name not in existing_columns:
                print(f"   Adding column: {field_name}")
                cursor.execute(f"ALTER TABLE Employees ADD COLUMN {field}")
        
        # Step 2: Check if we have data to migrate
        cursor.execute("SELECT COUNT(*) as count FROM AspNetUsers")
        user_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM Employees")
        employee_count = cursor.fetchone()['count']
        
        print(f"\n2. Found {user_count} users and {employee_count} employees")
        
        if user_count == 0:
            print("   No users to migrate.")
        else:
            print(f"   Migrating {user_count} users to Employees...")
            
            # Get all users with their roles
            cursor.execute("""
                SELECT u.*, GROUP_CONCAT(r.Name) as roles
                FROM AspNetUsers u
                LEFT JOIN AspNetUserRoles ur ON u.Id = ur.UserId
                LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
                GROUP BY u.Id
            """)
            
            users = cursor.fetchall()
            
            for user in users:
                user_id = user['Id']
                email = user['Email']
                employee_id = user['EmployeeId'] if 'EmployeeId' in user.keys() else None
                
                if employee_id:
                    # Update existing employee with auth data
                    print(f"   Updating employee {employee_id} with auth data from user {email}")
                    cursor.execute("""
                        UPDATE Employees
                        SET Email = ?, NormalizedEmail = ?, PasswordHash = ?,
                            SecurityStamp = ?, LockoutEnd = ?, AccessFailedCount = ?
                        WHERE Id = ?
                    """, (
                        user['Email'],
                        user['NormalizedEmail'],
                        user['PasswordHash'],
                        user['SecurityStamp'],
                        user['LockoutEnd'],
                        user['AccessFailedCount'],
                        employee_id
                    ))
                    
                    # Update role assignments to use EmployeeId instead of UserId
                    cursor.execute("""
                        UPDATE AspNetUserRoles
                        SET UserId = ?
                        WHERE UserId = ?
                    """, (str(employee_id), user_id))
                    
                else:
                    # Create new employee from user (user without employee link)
                    # Extract name from FullName if possible
                    full_name = user['FullName'] or email.split('@')[0]
                    parts = full_name.split()
                    vorname = parts[0] if len(parts) > 0 else "Unknown"
                    name = " ".join(parts[1:]) if len(parts) > 1 else "User"
                    
                    # Generate personnel number from user ID
                    personalnummer = f"U{user_id[:8]}"
                    
                    print(f"   Creating employee from user {email}")
                    cursor.execute("""
                        INSERT INTO Employees 
                        (Vorname, Name, Personalnummer, Email, NormalizedEmail, PasswordHash,
                         SecurityStamp, LockoutEnd, AccessFailedCount, Funktion,
                         IsFerienjobber, IsBrandmeldetechniker, IsBrandschutzbeauftragter,
                         IsTdQualified, IsTeamLeader, TeamId)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, NULL)
                    """, (
                        vorname, name, personalnummer,
                        user['Email'], user['NormalizedEmail'], user['PasswordHash'],
                        user['SecurityStamp'], user['LockoutEnd'], user['AccessFailedCount'],
                        "Benutzer"
                    ))
                    
                    new_employee_id = cursor.lastrowid
                    
                    # Update role assignments to use new EmployeeId
                    cursor.execute("""
                        UPDATE AspNetUserRoles
                        SET UserId = ?
                        WHERE UserId = ?
                    """, (str(new_employee_id), user_id))
        
        # Step 3: Rename AspNetUserRoles.UserId to EmployeeId for clarity
        print("\n3. Updating AspNetUserRoles to use EmployeeId...")
        print("   (Note: UserId column now contains EmployeeId values)")
        
        # Step 4: Update other tables that reference AspNetUsers
        print("\n4. Checking for other tables referencing AspNetUsers...")
        
        tables_to_check = ['AuditLogs', 'VacationRequests', 'ShiftAssignments', 'ShiftExchanges']
        for table in tables_to_check:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'CreatedBy' in columns or 'ModifiedBy' in columns or 'ProcessedBy' in columns:
                print(f"   Table {table} has user reference columns (no migration needed, uses email)")
        
        # Step 5: Create backup of AspNetUsers before deletion
        print("\n5. Creating backup of AspNetUsers table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AspNetUsers_Backup AS 
            SELECT * FROM AspNetUsers
        """)
        
        # Don't actually drop AspNetUsers yet - just mark migration complete
        print("\n✅ Migration completed successfully!")
        print()
        print("Summary:")
        print(f"  - Migrated {user_count} users to Employees table")
        print(f"  - Updated AspNetUserRoles to reference Employees")
        print(f"  - Created AspNetUsers_Backup table")
        print()
        print("⚠️  NOTE: AspNetUsers table is kept as backup.")
        print("         You can drop it manually after verifying the migration:")
        print("         DROP TABLE AspNetUsers;")
        print()
        print("Next steps:")
        print("  1. Test the application thoroughly")
        print("  2. Verify all users can login")
        print("  3. Check that all data is accessible")
        print("  4. If everything works, drop AspNetUsers_Backup")
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
    
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate database to merge Users and Employees tables'
    )
    parser.add_argument(
        'db_path', 
        nargs='?', 
        default='dienstplan.db',
        help='Path to database file (default: dienstplan.db)'
    )
    
    args = parser.parse_args()
    migrate_merge_users_employees(args.db_path)
