"""
Migration script: Add shift management system
- Adds IsActive, ModifiedAt, CreatedBy, ModifiedBy to ShiftTypes table
- Creates TeamShiftAssignments table
- Creates ShiftTypeRelationships table
- Adds indexes for new tables
- Migrates existing shifts to have IsActive=1
- Creates default team-shift assignments (all teams can work F, S, N by default)
"""

import sqlite3
import sys
from datetime import datetime


def migrate_database(db_path: str = "data/dienstplan.db"):
    """Run migration to add shift management tables and columns"""
    
    print("=" * 60)
    print("Starting Migration: Add Shift Management System")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Step 1: Add new columns to ShiftTypes if they don't exist
        print("\n[1/7] Adding new columns to ShiftTypes table...")
        
        # Check if IsActive column exists
        cursor.execute("PRAGMA table_info(ShiftTypes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'IsActive' not in columns:
            cursor.execute("ALTER TABLE ShiftTypes ADD COLUMN IsActive INTEGER NOT NULL DEFAULT 1")
            print("  ✓ Added IsActive column")
        else:
            print("  ℹ IsActive column already exists")
            
        if 'ModifiedAt' not in columns:
            cursor.execute("ALTER TABLE ShiftTypes ADD COLUMN ModifiedAt TEXT")
            print("  ✓ Added ModifiedAt column")
        else:
            print("  ℹ ModifiedAt column already exists")
            
        if 'CreatedBy' not in columns:
            cursor.execute("ALTER TABLE ShiftTypes ADD COLUMN CreatedBy TEXT")
            print("  ✓ Added CreatedBy column")
        else:
            print("  ℹ CreatedBy column already exists")
            
        if 'ModifiedBy' not in columns:
            cursor.execute("ALTER TABLE ShiftTypes ADD COLUMN ModifiedBy TEXT")
            print("  ✓ Added ModifiedBy column")
        else:
            print("  ℹ ModifiedBy column already exists")
        
        # Step 2: Create TeamShiftAssignments table
        print("\n[2/7] Creating TeamShiftAssignments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeamShiftAssignments (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                TeamId INTEGER NOT NULL,
                ShiftTypeId INTEGER NOT NULL,
                CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CreatedBy TEXT,
                FOREIGN KEY (TeamId) REFERENCES Teams(Id) ON DELETE CASCADE,
                FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
                UNIQUE(TeamId, ShiftTypeId)
            )
        """)
        print("  ✓ TeamShiftAssignments table created")
        
        # Step 3: Create ShiftTypeRelationships table
        print("\n[3/7] Creating ShiftTypeRelationships table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ShiftTypeRelationships (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                ShiftTypeId INTEGER NOT NULL,
                RelatedShiftTypeId INTEGER NOT NULL,
                DisplayOrder INTEGER NOT NULL,
                CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CreatedBy TEXT,
                FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
                FOREIGN KEY (RelatedShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
                UNIQUE(ShiftTypeId, RelatedShiftTypeId)
            )
        """)
        print("  ✓ ShiftTypeRelationships table created")
        
        # Step 4: Create indexes
        print("\n[4/7] Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teamshiftassignments_team 
            ON TeamShiftAssignments(TeamId)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teamshiftassignments_shift 
            ON TeamShiftAssignments(ShiftTypeId)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shifttyperelationships_shift 
            ON ShiftTypeRelationships(ShiftTypeId)
        """)
        print("  ✓ Indexes created")
        
        # Step 5: Set all existing shifts to IsActive=1
        print("\n[5/7] Setting existing shifts as active...")
        cursor.execute("UPDATE ShiftTypes SET IsActive = 1 WHERE IsActive IS NULL OR IsActive = 0")
        rows_updated = cursor.rowcount
        print(f"  ✓ Set {rows_updated} shifts to active")
        
        # Step 6: Create default team-shift assignments for main shifts (F, S, N)
        print("\n[6/7] Creating default team-shift assignments...")
        
        # Get all non-virtual teams
        cursor.execute("SELECT Id, Name FROM Teams WHERE IsVirtual = 0")
        teams = cursor.fetchall()
        
        # Get F, S, N shift types
        cursor.execute("SELECT Id, Code FROM ShiftTypes WHERE Code IN ('F', 'S', 'N')")
        shifts = cursor.fetchall()
        
        assignments_created = 0
        for team_id, team_name in teams:
            for shift_id, shift_code in shifts:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedBy)
                        VALUES (?, ?, 'migration')
                    """, (team_id, shift_id))
                    if cursor.rowcount > 0:
                        assignments_created += 1
                        print(f"  ✓ Assigned {shift_code} to {team_name}")
                except sqlite3.IntegrityError:
                    pass  # Already exists
        
        print(f"  ✓ Created {assignments_created} team-shift assignments")
        
        # Step 7: Create default shift relationships (F -> N -> S rotation)
        print("\n[7/7] Creating default shift relationships...")
        
        # Get shift IDs
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'F'")
        f_shift = cursor.fetchone()
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'N'")
        n_shift = cursor.fetchone()
        cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = 'S'")
        s_shift = cursor.fetchone()
        
        if f_shift and n_shift and s_shift:
            f_id, n_id, s_id = f_shift[0], n_shift[0], s_shift[0]
            
            # F -> N -> S rotation
            relationships = [
                (f_id, n_id, 1, "F -> N (order 1)"),
                (f_id, s_id, 2, "F -> S (order 2)"),
                (n_id, s_id, 1, "N -> S (order 1)"),
                (n_id, f_id, 2, "N -> F (order 2)"),
                (s_id, f_id, 1, "S -> F (order 1)"),
                (s_id, n_id, 2, "S -> N (order 2)"),
            ]
            
            for shift_id, related_id, order, desc in relationships:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO ShiftTypeRelationships 
                        (ShiftTypeId, RelatedShiftTypeId, DisplayOrder, CreatedBy)
                        VALUES (?, ?, ?, 'migration')
                    """, (shift_id, related_id, order))
                    if cursor.rowcount > 0:
                        print(f"  ✓ Created relationship: {desc}")
                except sqlite3.IntegrityError:
                    pass  # Already exists
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Remove virtual teams (98, 99) manually if needed")
        print("2. Update shift planning logic to use TeamShiftAssignments")
        print("3. Test the new shift management UI")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/dienstplan.db"
    
    migrate_database(db_path)
