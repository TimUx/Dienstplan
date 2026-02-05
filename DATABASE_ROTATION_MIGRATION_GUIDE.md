# Database-Driven Rotation Migration - Complete Guide

**Date**: 2026-02-05  
**Status**: ✅ IMPLEMENTED  
**Migration Script**: `migrate_to_rotation_groups.py`

## Overview

The Dienstplan shift planning system has been successfully migrated from hardcoded rotation patterns to database-driven rotation using the `RotationGroups` and `RotationGroupShifts` tables.

### What Changed

**Before Migration:**
- Rotation pattern hardcoded as `["F", "N", "S"]` in `constraints.py`
- No flexibility - all teams used same rotation
- Changes required code modifications

**After Migration:**
- Rotation patterns loaded from database
- Each team can have different rotation pattern
- Configurable via Admin UI
- Fallback to hardcoded pattern if database unavailable
- **Fully backward compatible**

---

## Migration Instructions

### For Existing Databases

If you have an existing `dienstplan.db` file, run the migration script:

```bash
python migrate_to_rotation_groups.py dienstplan.db
```

**The script will:**
1. ✅ Add `RotationGroupId` column to Teams table
2. ✅ Create default "Standard F→N→S" rotation group
3. ✅ Add F, N, S shifts to the rotation group in correct order
4. ✅ Link all existing teams to the default rotation group
5. ✅ Verify the migration succeeded

**Output Example:**
```
======================================================================
MIGRATION: Add Rotation Group Support to Teams
======================================================================
Database: dienstplan.db

[1/4] Adding RotationGroupId column to Teams table...
✅ Column added successfully

[2/4] Creating default rotation group (Standard F→N→S)...
✅ Created rotation group with ID: 1

[3/4] Adding shifts to default rotation group...
   ✅ Added F (order 1)
   ✅ Added N (order 2)
   ✅ Added S (order 3)

[4/4] Linking all teams to default rotation group...
   ✅ Linked 'Team Alpha' (ID: 1)
   ✅ Linked 'Team Beta' (ID: 2)
   ✅ Linked 'Team Gamma' (ID: 3)

======================================================================
✅ MIGRATION SUCCESSFUL
======================================================================
```

### For New Databases

New databases created with `db_init.py` automatically include:
- ✅ `RotationGroupId` column in Teams table
- ✅ Default "Standard F→N→S" rotation group
- ✅ All teams linked to default rotation

No manual migration needed! Just run:
```bash
python db_init.py dienstplan.db --with-sample-data
```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         WEB UI / API                            │
│  Admin can create/manage rotation groups via UI                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATABASE                                │
│                                                                 │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  RotationGroups      │      │  Teams               │        │
│  │  - Id                │◄─────┤  - Id                │        │
│  │  - Name              │      │  - Name              │        │
│  │  - Description       │      │  - RotationGroupId   │        │
│  │  - IsActive          │      └──────────────────────┘        │
│  └──────────┬───────────┘                                       │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────┐                                      │
│  │ RotationGroupShifts  │                                      │
│  │  - RotationGroupId   │                                      │
│  │  - ShiftTypeId       │                                      │
│  │  - RotationOrder     │ ◄── Defines sequence (1, 2, 3, ...)  │
│  └──────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ ✅ NOW CONNECTED!
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SOLVER / CONSTRAINTS                         │
│                                                                 │
│  data_loader.py:                                                │
│  └─ load_rotation_groups_from_db() → Dict[int, List[str]]      │
│                                                                 │
│  solver.py:                                                     │
│  └─ Loads patterns from database                               │
│  └─ Passes to constraints                                      │
│                                                                 │
│  constraints.py:                                                │
│  └─ add_team_rotation_constraints(rotation_patterns=...)       │
│     • Uses database pattern if team.rotation_group_id set      │
│     • Falls back to ["F", "N", "S"] if not                    │
└─────────────────────────────────────────────────────────────────┘
```

### Code Flow

1. **Solver Initialization**:
   ```python
   # solver.py
   rotation_patterns = load_rotation_groups_from_db(db_path)
   # Returns: {1: ["F", "N", "S"], 2: ["F", "S"], ...}
   ```

2. **Constraint Application**:
   ```python
   # For each team:
   if team.rotation_group_id and team.rotation_group_id in rotation_patterns:
       rotation = rotation_patterns[team.rotation_group_id]
   else:
       rotation = ["F", "N", "S"]  # Fallback
   ```

3. **Rotation Enforcement**:
   - Week-to-week rotation based on ISO week numbers
   - Each team follows its assigned pattern
   - Offset by team index for coverage

---

## Using Custom Rotation Patterns

### Via Database

You can create custom rotation groups directly in the database:

```sql
-- Create a 2-shift rotation (F → S)
INSERT INTO RotationGroups (Name, Description, IsActive)
VALUES ('2-Shift F→S', 'Two-shift rotation: Früh and Spät only', 1);

-- Get the ID (let's say it's 2)
-- Add shifts in order
INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder)
VALUES 
    (2, 1, 1),  -- F first
    (2, 2, 2);  -- S second

-- Assign a team to this rotation group
UPDATE Teams 
SET RotationGroupId = 2 
WHERE Id = 1;
```

### Via Admin UI

*(Once UI is updated - currently read-only)*

1. Navigate to Admin → Rotation Groups
2. Click "Add New Rotation Group"
3. Enter name and description
4. Select shifts and set their order
5. Save
6. Go to Teams and assign the rotation group

---

## Examples

### Standard 3-Shift Rotation (Default)

```
Rotation Group: "Standard F→N→S"
Shifts: F (order 1) → N (order 2) → S (order 3)

Week 1: Team A=F, Team B=N, Team C=S
Week 2: Team A=N, Team B=S, Team C=F
Week 3: Team A=S, Team B=F, Team C=N
Week 4: Team A=F, Team B=N, Team C=S  (repeats)
```

### Custom 2-Shift Rotation

```
Rotation Group: "2-Shift F→S"
Shifts: F (order 1) → S (order 2)

Week 1: Team A=F, Team B=S
Week 2: Team A=S, Team B=F
Week 3: Team A=F, Team B=S  (repeats)
```

### Reverse Rotation

```
Rotation Group: "Reverse S→N→F"
Shifts: S (order 1) → N (order 2) → F (order 3)

Week 1: Team A=S, Team B=N, Team C=F
Week 2: Team A=N, Team B=F, Team C=S
Week 3: Team A=F, Team B=S, Team C=N
```

---

## Testing

### Verify Migration

After running the migration script:

```bash
# Check rotation groups
sqlite3 dienstplan.db "SELECT * FROM RotationGroups;"

# Check rotation group shifts
sqlite3 dienstplan.db "
SELECT rg.Name, st.Code, rgs.RotationOrder
FROM RotationGroupShifts rgs
JOIN RotationGroups rg ON rg.Id = rgs.RotationGroupId
JOIN ShiftTypes st ON st.Id = rgs.ShiftTypeId
ORDER BY rg.Id, rgs.RotationOrder;
"

# Check team assignments
sqlite3 dienstplan.db "
SELECT t.Name, rg.Name
FROM Teams t
LEFT JOIN RotationGroups rg ON rg.Id = t.RotationGroupId
WHERE t.IsVirtual = 0;
"
```

### Run Test Suite

```bash
# Test database-driven rotation
python test_database_rotation.py

# Test existing rotation behavior (backward compatibility)
python test_rotation_order.py
```

Expected output: **✅ ALL TESTS PASSED!**

---

## Troubleshooting

### Issue: Teams not rotating

**Check 1**: Verify team has rotation group assigned
```sql
SELECT Id, Name, RotationGroupId FROM Teams WHERE IsVirtual = 0;
```

**Solution**: Assign rotation group to team
```sql
UPDATE Teams SET RotationGroupId = 1 WHERE Id = <team_id>;
```

**Check 2**: Verify rotation group has shifts
```sql
SELECT * FROM RotationGroupShifts WHERE RotationGroupId = 1;
```

**Solution**: Add shifts to rotation group (see migration script example)

### Issue: Solver uses hardcoded pattern

**Check**: Look for this message in solver output:
```
- Team rotation (FALLBACK: Using hardcoded F → N → S pattern)
```

**Possible Causes**:
1. Database file not found at specified path
2. Teams don't have `RotationGroupId` set
3. Rotation group doesn't have shifts configured

**Solution**: Run migration script or check database configuration

### Issue: Migration fails

**Error**: "column RotationGroupId already exists"

**Solution**: Migration already applied. Check with:
```sql
PRAGMA table_info(Teams);
```

If column exists but teams aren't linked, manually link them:
```sql
UPDATE Teams 
SET RotationGroupId = 1 
WHERE IsVirtual = 0 AND RotationGroupId IS NULL;
```

---

## API Reference

### load_rotation_groups_from_db()

```python
from data_loader import load_rotation_groups_from_db

# Load all active rotation patterns
patterns = load_rotation_groups_from_db("dienstplan.db")

# Returns:
# {
#     1: ["F", "N", "S"],      # Rotation group 1
#     2: ["F", "S"],            # Rotation group 2
#     3: ["N", "S", "F"]        # Rotation group 3
# }
```

### Solver with Custom Database Path

```python
from solver import ShiftPlanningSolver

solver = ShiftPlanningSolver(
    planning_model,
    time_limit_seconds=300,
    db_path="/path/to/database.db"  # Custom database path
)
```

---

## Migration Checklist

For system administrators migrating existing installations:

- [ ] 1. Backup existing database
- [ ] 2. Test migration on backup first
- [ ] 3. Run migration script on production database
- [ ] 4. Verify migration with SQL queries
- [ ] 5. Run test suite to ensure functionality
- [ ] 6. Check solver output for "DATABASE-DRIVEN" message
- [ ] 7. Verify first schedule generation uses database patterns
- [ ] 8. Update team documentation if custom patterns needed
- [ ] 9. Train admins on creating custom rotation groups (when UI ready)

---

## Benefits

### For Administrators
- ✅ Configure rotation patterns without code changes
- ✅ Different teams can have different patterns
- ✅ Easy to test new rotation patterns
- ✅ Changes take effect immediately

### For Developers
- ✅ Clean separation of data and logic
- ✅ Easier to maintain and test
- ✅ Backward compatible - no breaking changes
- ✅ Extensible for future features

### For End Users
- ✅ More flexible shift planning
- ✅ Better team-specific configurations
- ✅ Improved schedule quality

---

## Future Enhancements

Possible improvements:

1. **UI Enhancements**:
   - Drag-and-drop rotation pattern builder
   - Visual rotation preview
   - Team-to-rotation assignment interface

2. **Advanced Patterns**:
   - Time-based rotation changes (summer vs winter patterns)
   - Holiday-specific rotations
   - Multi-week patterns (e.g., 4-week cycles)

3. **Validation**:
   - Warn if rotation pattern can't meet staffing requirements
   - Suggest optimal team count for pattern
   - Validate shift type availability

4. **Reporting**:
   - Rotation adherence reports
   - Pattern effectiveness metrics
   - Team workload balance analysis

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review test files for examples
3. Consult source code documentation
4. Contact development team

---

**Migration Script**: `migrate_to_rotation_groups.py`  
**Test Suite**: `test_database_rotation.py`  
**Documentation Updated**: 2026-02-05  
**Status**: ✅ PRODUCTION READY
