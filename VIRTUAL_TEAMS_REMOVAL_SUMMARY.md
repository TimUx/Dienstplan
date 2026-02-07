# Virtual Teams Removal - Complete Summary

## Overview
Virtual teams were a feature that is no longer used in the system. This PR completely removes all references to virtual teams from the codebase, including code, database schema, and API responses.

## Problem Statement
The system info export showed:
```
Team Statistics:
  Regular Teams: 3
  Virtual Teams: 0
  Total: 3
```

This indicated that virtual team references remained throughout the codebase despite not being actively used.

## Changes Made

### 1. Database Schema Change

**Before:**
```sql
CREATE TABLE Teams (
    Id INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Description TEXT,
    Email TEXT,
    IsVirtual INTEGER NOT NULL DEFAULT 0,  -- ← REMOVED
    RotationGroupId INTEGER,
    CreatedAt TEXT
)
```

**After:**
```sql
CREATE TABLE Teams (
    Id INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Description TEXT,
    Email TEXT,
    RotationGroupId INTEGER,
    CreatedAt TEXT
)
```

### 2. Entity Model Change

**Before:**
```python
@dataclass
class Team:
    id: int
    name: str
    description: Optional[str] = None
    email: Optional[str] = None
    is_virtual: bool = False  # ← REMOVED
    rotation_group_id: Optional[int] = None
    employees: List[Employee] = field(default_factory=list)
    allowed_shift_type_ids: List[int] = field(default_factory=list)
```

**After:**
```python
@dataclass
class Team:
    id: int
    name: str
    description: Optional[str] = None
    email: Optional[str] = None
    rotation_group_id: Optional[int] = None
    employees: List[Employee] = field(default_factory=list)
    allowed_shift_type_ids: List[int] = field(default_factory=list)
```

### 3. API Response Change

**Before:**
```json
{
  "id": 1,
  "name": "Team Alpha",
  "description": "First team",
  "email": "team.alpha@example.com",
  "isVirtual": false,
  "employeeCount": 5
}
```

**After:**
```json
{
  "id": 1,
  "name": "Team Alpha",
  "description": "First team",
  "email": "team.alpha@example.com",
  "employeeCount": 5
}
```

### 4. Statistics Output Change

**Before:**
```
Team Statistics:
  Regular Teams: 3
  Virtual Teams: 0
  Total: 3

Team [1]: Team Alpha [VIRTUAL]
```

**After:**
```
Team Statistics:
  Total Teams: 3

Team [1]: Team Alpha
```

## Files Modified

| File | Changes |
|------|---------|
| `entities.py` | Removed `is_virtual` field from Team dataclass |
| `data_loader.py` | Removed IsVirtual from queries, removed validation checks |
| `db_init.py` | Removed IsVirtual from schema and sample data |
| `web_api.py` | Removed virtual team function, queries, and API fields |
| `export_system_info.py` | Simplified statistics, removed [VIRTUAL] markers |
| `migrate_remove_virtual_teams.py` | **NEW**: Migration script for existing databases |

## Code Changes Summary

- **Files changed**: 6 (5 updated, 1 new)
- **Lines removed**: ~92
- **Lines added**: ~41 (excluding migration script)
- **Net change**: -51 lines
- **Migration script**: +121 lines

## Migration Instructions

### For New Databases
No action needed. The new schema is automatically applied when running `db_init.py`.

### For Existing Databases
Run the migration script:

```bash
# Backup first (recommended)
cp dienstplan.db dienstplan.db.backup

# Run migration
python migrate_remove_virtual_teams.py dienstplan.db

# Verify
python export_system_info.py --db dienstplan.db
```

The migration script:
- ✅ Checks if IsVirtual column exists
- ✅ Creates new table without IsVirtual
- ✅ Copies all data safely
- ✅ Drops old table and renames new one
- ✅ Preserves all team information

## Verification

All verification tests pass:

1. ✅ Team entity has no `is_virtual` field
2. ✅ data_loader imports correctly
3. ✅ export_system_info uses "Total Teams"
4. ✅ web_api has no virtual references
5. ✅ DB schema has no IsVirtual column
6. ✅ Migration script exists and compiles

## Breaking Changes

⚠️ **API Breaking Change**: The `isVirtual` field has been removed from team API responses.

If you have client code that references `team.isVirtual`, you should remove those references as the field no longer exists.

## Benefits

1. **Simplified Code**: Removed unused functionality reduces maintenance burden
2. **Clearer Intent**: No confusion about what virtual teams were or if they're supported
3. **Better Performance**: Fewer database columns and simpler queries
4. **Accurate Statistics**: System info now accurately reflects the single team concept
5. **Reduced Complexity**: Removed special handling logic throughout the codebase

## Testing

- ✅ All modified files compile without errors
- ✅ Migration script tested on sample database
- ✅ Export system info verified with correct output
- ✅ No [VIRTUAL] markers in team listings
- ✅ API responses no longer include isVirtual field

## Status

**COMPLETED ✅**

Date: 2026-02-07
