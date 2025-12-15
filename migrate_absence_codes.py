"""
Database migration script for absence code standardization.

This script updates an existing database to support:
- Official absence codes (U, AU, L)
- Virtual team "Fire Alarm System"
- Removal of virtual "Springer" team
- TD qualification tracking
"""

import sqlite3
import sys
import os


def migrate_database(db_path: str):
    """
    Migrate database to support new absence code system.
    
    Args:
        db_path: Path to SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"✗ Database not found: {db_path}")
        return False
    
    print("="*60)
    print("DATABASE MIGRATION: Absence Code Standardization")
    print("="*60)
    print(f"Database: {db_path}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Add IsVirtual column to Teams if not exists
        print("[1/6] Adding IsVirtual column to Teams table...")
        try:
            cursor.execute("ALTER TABLE Teams ADD COLUMN IsVirtual INTEGER NOT NULL DEFAULT 0")
            print("      ✓ Added IsVirtual column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("      → IsVirtual column already exists")
            else:
                raise
        
        # 2. Add IsTdQualified column to Employees if not exists
        print("\n[2/6] Adding IsTdQualified column to Employees table...")
        try:
            cursor.execute("ALTER TABLE Employees ADD COLUMN IsTdQualified INTEGER NOT NULL DEFAULT 0")
            print("      ✓ Added IsTdQualified column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("      → IsTdQualified column already exists")
            else:
                raise
        
        # 3. Update TD qualification based on BMT/BSB flags
        print("\n[3/6] Updating TD qualification for employees...")
        cursor.execute("""
            UPDATE Employees 
            SET IsTdQualified = 1 
            WHERE IsBrandmeldetechniker = 1 OR IsBrandschutzbeauftragter = 1
        """)
        updated = cursor.rowcount
        print(f"      ✓ Updated {updated} employees with TD qualification")
        
        # 4. Check for "Springer" virtual team and remove if exists
        print("\n[4/6] Removing virtual 'Springer' team (if exists)...")
        cursor.execute("SELECT Id FROM Teams WHERE Name = 'Springer' AND IsVirtual = 1")
        springer_team = cursor.fetchone()
        if springer_team:
            springer_id = springer_team[0]
            
            # Update employees in springer team to have no team
            cursor.execute("UPDATE Employees SET TeamId = NULL WHERE TeamId = ?", (springer_id,))
            moved = cursor.rowcount
            
            # Delete the team
            cursor.execute("DELETE FROM Teams WHERE Id = ?", (springer_id,))
            
            print(f"      ✓ Removed virtual 'Springer' team (ID: {springer_id})")
            print(f"        → Moved {moved} employees out of springer team")
        else:
            print("      → No virtual 'Springer' team found")
        
        # 5. Add "Fire Alarm System" virtual team if not exists
        print("\n[5/6] Creating 'Fire Alarm System' virtual team...")
        cursor.execute("SELECT Id FROM Teams WHERE Name = 'Fire Alarm System'")
        fire_alarm_team = cursor.fetchone()
        
        if not fire_alarm_team:
            cursor.execute("""
                INSERT INTO Teams (Name, Description, Email, IsVirtual)
                VALUES ('Fire Alarm System', 
                        'Virtual team for BSB/BMT qualified employees', 
                        'feuermeldeanl@fritzwinter.de', 
                        1)
            """)
            fire_alarm_id = cursor.lastrowid
            print(f"      ✓ Created 'Fire Alarm System' virtual team (ID: {fire_alarm_id})")
            
            # Optionally assign TD-qualified employees without a team to Fire Alarm System
            cursor.execute("""
                UPDATE Employees 
                SET TeamId = ? 
                WHERE IsTdQualified = 1 AND TeamId IS NULL AND IsSpringer = 0
            """, (fire_alarm_id,))
            assigned = cursor.rowcount
            if assigned > 0:
                print(f"        → Assigned {assigned} TD-qualified employees to Fire Alarm System")
        else:
            fire_alarm_id = fire_alarm_team[0]
            print(f"      → 'Fire Alarm System' team already exists (ID: {fire_alarm_id})")
        
        # 6. Verify absence data
        print("\n[6/6] Verifying absence data...")
        cursor.execute("SELECT COUNT(*) FROM Absences")
        absence_count = cursor.fetchone()[0]
        print(f"      ✓ Found {absence_count} absence records")
        
        # Show absence type distribution
        cursor.execute("""
            SELECT Type, COUNT(*) 
            FROM Absences 
            GROUP BY Type
        """)
        type_dist = cursor.fetchall()
        if type_dist:
            print("        Absence type distribution:")
            type_names = {1: "AU (Krank)", 2: "U (Urlaub)", 3: "L (Lehrgang)"}
            for type_id, count in type_dist:
                type_name = type_names.get(type_id, f"Unknown ({type_id})")
                print(f"          - {type_name}: {count}")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*60)
        print("✓✓✓ MIGRATION COMPLETED SUCCESSFULLY ✓✓✓")
        print("="*60)
        
        print("\nOFFICIAL ABSENCE CODES:")
        print("  - U  = Urlaub (Vacation)")
        print("  - AU = Arbeitsunfähigkeit / Krank (Sick leave / Medical certificate)")
        print("  - L  = Lehrgang (Training / Course)")
        
        print("\nFORBIDDEN CODES (must not be used):")
        print("  - V  = FORBIDDEN")
        print("  - K  = FORBIDDEN")
        
        print("\nSYSTEM CHANGES:")
        print("  ✓ Virtual team 'Fire Alarm System' created for display grouping")
        print("  ✓ Virtual 'Springer' team removed (springers are employee attributes)")
        print("  ✓ TD qualification tracking enabled")
        print("  ✓ Absences always override shifts and TD")
        
        print("\nNEXT STEPS:")
        print("  1. Test the migration:")
        print("     python test_absence_codes.py")
        print("  2. Generate a test schedule:")
        print("     python main.py plan --start-date 2025-01-01 --end-date 2025-01-31")
        print("  3. Verify absence visibility in all views")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    
    finally:
        conn.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python migrate_absence_codes.py <database_path>")
        print("\nExample:")
        print("  python migrate_absence_codes.py dienstplan.db")
        print("  python migrate_absence_codes.py data/production.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    success = migrate_database(db_path)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
