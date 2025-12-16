# Database Migration Guide: Absence Code Updates

## Overview

This document describes the database changes needed to support the official absence code standard (U, AU, L).

## Changes Required

### 1. Absence Type Mapping

**Old System:**
- Database stored integer types: 1=Krank, 2=Urlaub, 3=Lehrgang
- Display used German words

**New System:**
- Database still uses integers (for compatibility)
- Official codes: U (Urlaub), AU (Arbeitsunfähigkeit), L (Lehrgang)
- Mapping in code:
  - Type 1 → AU (Sick leave / Medical certificate)
  - Type 2 → U (Vacation)
  - Type 3 → L (Training / Course)

### 2. Teams Table

Add `IsVirtual` column to support virtual teams:

```sql
ALTER TABLE Teams ADD COLUMN IsVirtual INTEGER NOT NULL DEFAULT 0;
```

### 3. Employees Table

Add TD qualification tracking:

```sql
ALTER TABLE Employees ADD COLUMN IsTdQualified INTEGER NOT NULL DEFAULT 0;
```

Update TD qualification based on existing BMT/BSB flags:

```sql
UPDATE Employees 
SET IsTdQualified = 1 
WHERE IsBrandmeldetechniker = 1 OR IsBrandschutzbeauftragter = 1;
```

### 4. ShiftTypes Table

Remove old absence shift types (they are now handled via Absences table):

```sql
-- Mark old shift types as deprecated but don't delete (for historical data)
-- New schedules will not use these
-- Absence codes K, U, L in ShiftTypes are NO LONGER USED
```

### 5. Virtual Teams

Add "Fire Alarm System" virtual team:

```sql
INSERT INTO Teams (Name, Description, Email, IsVirtual)
VALUES ('Fire Alarm System', 
        'Virtual team for BSB/BMT qualified employees', 
        'feuermeldeanl@fritzwinter.de', 
        1);
```

Remove "Springer" virtual team if it exists:

```sql
DELETE FROM Teams WHERE Name = 'Springer' AND IsVirtual = 1;
```

## Migration Script

Run this script to migrate an existing database:

```python
import sqlite3

def migrate_database(db_path: str):
    """Migrate database to support new absence code system"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    # 1. Add IsVirtual column to Teams if not exists
    try:
        cursor.execute("ALTER TABLE Teams ADD COLUMN IsVirtual INTEGER NOT NULL DEFAULT 0")
        print("✓ Added IsVirtual column to Teams table")
    except sqlite3.OperationalError:
        print("  IsVirtual column already exists")
    
    # 2. Add IsTdQualified column to Employees if not exists
    try:
        cursor.execute("ALTER TABLE Employees ADD COLUMN IsTdQualified INTEGER NOT NULL DEFAULT 0")
        print("✓ Added IsTdQualified column to Employees table")
    except sqlite3.OperationalError:
        print("  IsTdQualified column already exists")
    
    # 3. Update TD qualification based on BMT/BSB flags
    cursor.execute("""
        UPDATE Employees 
        SET IsTdQualified = 1 
        WHERE IsBrandmeldetechniker = 1 OR IsBrandschutzbeauftragter = 1
    """)
    updated = cursor.rowcount
    print(f"✓ Updated {updated} employees with TD qualification")
    
    # 4. Check for "Springer" virtual team and remove if exists
    cursor.execute("SELECT Id FROM Teams WHERE Name = 'Springer' AND IsVirtual = 1")
    springer_team = cursor.fetchone()
    if springer_team:
        # Update employees in springer team to have no team
        cursor.execute("UPDATE Employees SET TeamId = NULL WHERE TeamId = ?", (springer_team[0],))
        cursor.execute("DELETE FROM Teams WHERE Id = ?", (springer_team[0],))
        print("✓ Removed virtual 'Springer' team")
    else:
        print("  No virtual 'Springer' team found")
    
    # 5. Add "Fire Alarm System" virtual team if not exists
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
        print(f"✓ Created 'Fire Alarm System' virtual team (ID: {fire_alarm_id})")
        
        # Optionally assign TD-qualified employees without a team to Fire Alarm System
        cursor.execute("""
            UPDATE Employees 
            SET TeamId = ? 
            WHERE IsTdQualified = 1 AND TeamId IS NULL AND IsSpringer = 0
        """, (fire_alarm_id,))
        assigned = cursor.rowcount
        print(f"  Assigned {assigned} TD-qualified employees to Fire Alarm System")
    else:
        print("  'Fire Alarm System' team already exists")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Migration completed successfully!")
    print("\nNOTE: Absence codes are now:")
    print("  - U  = Urlaub (Vacation)")
    print("  - AU = Krank / Arbeitsunfähigkeit (Sick leave)")
    print("  - L  = Lehrgang (Training)")
    print("\nOld shift type codes K, U, L are deprecated.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python migrate_absence_codes.py <database_path>")
        sys.exit(1)
    
    migrate_database(sys.argv[1])
```

## Verification

After migration, verify:

1. **Absence Codes**: All absences load with correct codes (U, AU, L)
2. **Virtual Teams**: "Fire Alarm System" exists, "Springer" team removed
3. **TD Qualification**: Employees with BMT or BSB have IsTdQualified=1
4. **Springers**: Springers are employees (not a team), can belong to any team or no team

## Rollback

If you need to rollback:

```sql
-- Note: IsVirtual and IsTdQualified columns can remain (they won't break old code)
-- But if you need to remove them:

-- Remove Fire Alarm System team
DELETE FROM Teams WHERE Name = 'Fire Alarm System' AND IsVirtual = 1;

-- Recreate Springer team (if needed by old system)
INSERT INTO Teams (Name, Description, Email, IsVirtual)
VALUES ('Springer', 'Virtuelles Team für Springer', 'springer@fritzwinter.de', 1);
```

## Testing

Test the migration:

```bash
# Run migration
python migrate_absence_codes.py dienstplan.db

# Test with Python
python test_absence_codes.py

# Verify absence codes in schedule
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --db dienstplan.db
```
