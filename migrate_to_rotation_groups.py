#!/usr/bin/env python3
"""
Migration script: Add RotationGroupId to Teams table and create default rotation group.

This migration enables database-driven shift rotation patterns instead of hardcoded F→N→S.

Usage:
    python migrate_to_rotation_groups.py [db_path]
    
Default db_path: dienstplan.db
"""

import sqlite3
import sys
from datetime import datetime


def migrate_add_rotation_group_to_teams(db_path: str = "dienstplan.db"):
    """
    Add RotationGroupId column to Teams table and create default rotation group.
    
    Steps:
    1. Add RotationGroupId column to Teams table
    2. Create default "Standard F→N→S" rotation group
    3. Link all existing teams to the default rotation group
    4. Verify the migration
    """
    print("=" * 70)
    print("MIGRATION: Add Rotation Group Support to Teams")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(Teams)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'RotationGroupId' in columns:
            print("⚠️  Migration already applied - RotationGroupId column exists")
            print()
            return
        
        print("[1/4] Adding RotationGroupId column to Teams table...")
        cursor.execute("""
            ALTER TABLE Teams 
            ADD COLUMN RotationGroupId INTEGER 
            REFERENCES RotationGroups(Id)
        """)
        print("✅ Column added successfully")
        print()
        
        print("[2/4] Creating default rotation group (Standard F→N→S)...")
        cursor.execute("""
            INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy)
            VALUES (?, ?, 1, ?)
        """, (
            "Standard F→N→S",
            "Standard 3-Schicht-Rotation: Frühdienst → Nachtdienst → Spätdienst",
            "System Migration"
        ))
        default_rotation_group_id = cursor.lastrowid
        print(f"✅ Created rotation group with ID: {default_rotation_group_id}")
        print()
        
        print("[3/4] Adding shifts to default rotation group...")
        # Get shift type IDs for F, N, S
        cursor.execute("SELECT Id, Code FROM ShiftTypes WHERE Code IN ('F', 'N', 'S')")
        shift_types = {row[1]: row[0] for row in cursor.fetchall()}
        
        if len(shift_types) != 3:
            print(f"⚠️  Warning: Expected 3 shift types (F, N, S), found {len(shift_types)}")
            print(f"   Available shift types: {list(shift_types.keys())}")
        
        # Add shifts in rotation order: F=1, N=2, S=3
        rotation_order = [('F', 1), ('N', 2), ('S', 3)]
        for shift_code, order in rotation_order:
            if shift_code in shift_types:
                cursor.execute("""
                    INSERT INTO RotationGroupShifts 
                    (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                    VALUES (?, ?, ?, ?)
                """, (default_rotation_group_id, shift_types[shift_code], order, "System Migration"))
                print(f"   ✅ Added {shift_code} (order {order})")
            else:
                print(f"   ⚠️  Shift type {shift_code} not found, skipping")
        print()
        
        print("[4/4] Linking all teams to default rotation group...")
        cursor.execute("SELECT Id, Name FROM Teams WHERE IsVirtual = 0")
        teams = cursor.fetchall()
        
        if teams:
            for team_id, team_name in teams:
                cursor.execute("""
                    UPDATE Teams 
                    SET RotationGroupId = ? 
                    WHERE Id = ?
                """, (default_rotation_group_id, team_id))
                print(f"   ✅ Linked '{team_name}' (ID: {team_id})")
            print()
        else:
            print("   ℹ️  No teams found to link")
            print()
        
        # Commit all changes
        conn.commit()
        
        print("=" * 70)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  • RotationGroupId column added to Teams table")
        print(f"  • Default rotation group created (ID: {default_rotation_group_id})")
        print(f"  • {len(teams)} team(s) linked to default rotation")
        print()
        print("Next steps:")
        print("  • Restart the application to use database-driven rotation")
        print("  • Use the web UI to create custom rotation groups if needed")
        print("  • Assign teams to custom rotation groups via Admin panel")
        print()
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_migration(db_path: str = "dienstplan.db"):
    """Verify that the migration was successful."""
    print("Verifying migration...")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check column exists
        cursor.execute("PRAGMA table_info(Teams)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'RotationGroupId' in columns, "RotationGroupId column not found"
        print("✅ RotationGroupId column exists in Teams table")
        
        # Check default rotation group exists
        cursor.execute("""
            SELECT Id, Name, Description 
            FROM RotationGroups 
            WHERE Name = 'Standard F→N→S'
        """)
        rotation_group = cursor.fetchone()
        assert rotation_group is not None, "Default rotation group not found"
        group_id, name, desc = rotation_group
        print(f"✅ Default rotation group found: {name} (ID: {group_id})")
        
        # Check rotation group has shifts
        cursor.execute("""
            SELECT st.Code, rgs.RotationOrder
            FROM RotationGroupShifts rgs
            JOIN ShiftTypes st ON st.Id = rgs.ShiftTypeId
            WHERE rgs.RotationGroupId = ?
            ORDER BY rgs.RotationOrder
        """, (group_id,))
        shifts = cursor.fetchall()
        assert len(shifts) == 3, f"Expected 3 shifts, found {len(shifts)}"
        shift_codes = [s[0] for s in shifts]
        assert shift_codes == ['F', 'N', 'S'], f"Expected ['F', 'N', 'S'], got {shift_codes}"
        print(f"✅ Rotation pattern configured: {' → '.join(shift_codes)}")
        
        # Check teams are linked
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Teams 
            WHERE RotationGroupId = ? AND IsVirtual = 0
        """, (group_id,))
        team_count = cursor.fetchone()[0]
        print(f"✅ {team_count} team(s) linked to default rotation")
        
        print()
        print("✅ Verification successful - migration is complete!")
        
    except AssertionError as e:
        print(f"❌ Verification failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "dienstplan.db"
    
    try:
        migrate_add_rotation_group_to_teams(db_path)
        verify_migration(db_path)
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        sys.exit(1)
