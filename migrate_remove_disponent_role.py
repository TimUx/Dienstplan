"""
Migration script to remove Disponent role and migrate users to Admin role.
All users with Disponent role will be converted to Admin role.
"""

import sqlite3
import sys


def migrate_remove_disponent_role(db_path: str = "dienstplan.db"):
    """
    Remove Disponent role and convert all Disponent users to Admin.
    
    Args:
        db_path: Path to SQLite database
    """
    print(f"🔧 Starting migration: Remove Disponent role")
    print(f"Database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if Disponent role exists
        cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = 'Disponent'")
        disponent_role = cursor.fetchone()
        
        if not disponent_role:
            print("⚠️  Disponent role does not exist in database")
            print("Migration not needed.")
            return
        
        disponent_role_id = disponent_role[0]
        
        # Get Admin role ID
        cursor.execute("SELECT Id FROM AspNetRoles WHERE Name = 'Admin'")
        admin_role = cursor.fetchone()
        
        if not admin_role:
            print("❌ Admin role not found! Creating it...")
            admin_role_id = "admin-role-id"
            cursor.execute("""
                INSERT INTO AspNetRoles (Id, Name, NormalizedName)
                VALUES (?, 'Admin', 'ADMIN')
            """, (admin_role_id,))
        else:
            admin_role_id = admin_role[0]
        
        # Find all users with Disponent role
        cursor.execute("""
            SELECT UserId FROM AspNetUserRoles WHERE RoleId = ?
        """, (disponent_role_id,))
        
        disponent_users = cursor.fetchall()
        user_count = len(disponent_users)
        
        print(f"Found {user_count} user(s) with Disponent role")
        
        if user_count > 0:
            print("Converting Disponent users to Admin role...")
            
            for user_row in disponent_users:
                user_id = user_row[0]
                
                # Check if user already has Admin role
                cursor.execute("""
                    SELECT 1 FROM AspNetUserRoles 
                    WHERE UserId = ? AND RoleId = ?
                """, (user_id, admin_role_id))
                
                if cursor.fetchone():
                    print(f"  - User {user_id} already has Admin role, removing Disponent...")
                    cursor.execute("""
                        DELETE FROM AspNetUserRoles 
                        WHERE UserId = ? AND RoleId = ?
                    """, (user_id, disponent_role_id))
                else:
                    print(f"  - Converting user {user_id} from Disponent to Admin...")
                    cursor.execute("""
                        UPDATE AspNetUserRoles 
                        SET RoleId = ? 
                        WHERE UserId = ? AND RoleId = ?
                    """, (admin_role_id, user_id, disponent_role_id))
        
        # Delete Disponent role
        print("Deleting Disponent role...")
        cursor.execute("DELETE FROM AspNetRoles WHERE Id = ?", (disponent_role_id,))
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print()
        print(f"Summary:")
        print(f"  - Converted {user_count} Disponent user(s) to Admin role")
        print(f"  - Removed Disponent role from database")
        
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
        description='Migrate database to remove Disponent role'
    )
    parser.add_argument(
        'db_path', 
        nargs='?', 
        default='dienstplan.db',
        help='Path to database file (default: dienstplan.db)'
    )
    
    args = parser.parse_args()
    migrate_remove_disponent_role(args.db_path)
