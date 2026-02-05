# Shift Rotation Investigation - Quick Reference

**Investigation Date**: 2026-02-05  
**Issue**: Check if shift rotation is hardcoded or uses database RotationGroups  
**Result**: ✅ HARDCODED (Database tables exist but unused)

---

## Quick Answer

### Question (German)
> Prüfe wie die Schichtrotation umgesetzt ist. Ist diese Hardcoded oder wird die Einstellung in der Datenbank über die Rotationsgruppen verwendet?

### Answer
The shift rotation pattern **F → N → S is HARDCODED** in `constraints.py` and does **NOT use** the database `RotationGroups` tables.

---

## Evidence

### 1. Hardcoded Pattern Location
```python
# File: constraints.py, line 47
ROTATION_PATTERN = ["F", "N", "S"]
```

### 2. Used In Two Functions
- `add_team_rotation_constraints()` - HARD constraint for teams
- `add_employee_weekly_rotation_order_constraints()` - SOFT constraint with 10K penalty

### 3. Database Tables Status
- **Tables**: `RotationGroups`, `RotationGroupShifts` ✅ Exist
- **API Endpoints**: `/api/rotationgroups` ✅ Exist
- **Web UI**: Admin can manage groups ✅ Exists
- **Solver Integration**: ❌ **NOT CONNECTED** - Never loaded or used

---

## Key Files

| File | Role | Uses DB? |
|------|------|----------|
| `constraints.py` | Rotation logic | ❌ No - hardcoded |
| `solver.py` | Solver integration | ❌ No |
| `data_loader.py` | Data loading | ❌ No - doesn't load RotationGroups |
| `db_init.py` | Database schema | ✅ Defines tables (unused) |
| `web_api.py` | REST API | ✅ Manages RotationGroups (not used by solver) |
| `entities.py` | Data models | ✅ Defines classes (not used) |

---

## Architecture Diagram

```
┌─────────────────────┐
│   WEB UI / API      │  ← Admin can manage RotationGroups
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    DATABASE         │
│  RotationGroups     │  ← Tables exist
│  RotationGroupShifts│
└──────────┬──────────┘
           │
           │ ❌ NO CONNECTION!
           │
           ▼
┌─────────────────────┐
│   SOLVER            │
│  constraints.py     │  ← Uses ROTATION_PATTERN = ["F", "N", "S"]
│  (HARDCODED)        │
└─────────────────────┘
```

---

## Full Documentation

For detailed analysis and migration options, see:

1. **German Version**: `ROTATION_IMPLEMENTATION_ANALYSIS.md` (22KB)
   - Complete analysis in German
   - Migration options A, B, C
   - Example code for migration

2. **English Version**: `ROTATION_IMPLEMENTATION_ANALYSIS_EN.md` (21KB)
   - Complete analysis in English
   - Migration options A, B, C
   - Example code for migration

---

## Recommendations

### Option A: Keep Current State (Recommended)
- ✅ Simple, no changes needed
- ⚠️ Add UI warning that RotationGroups have no effect
- ⚠️ Or remove RotationGroups UI entirely

### Option B: Migrate to Database (2-3 days)
- Load RotationGroups from database
- Connect to solver/constraints
- Full flexibility for different patterns

### Option C: Hybrid (Medium effort)
- Database patterns with hardcoded fallback
- Gradual migration path
- Minimal breaking changes

---

## Conclusion

**Current Situation**:
- Rotation is **100% hardcoded** as `["F", "N", "S"]`
- Database infrastructure exists but is **decoration only**
- UI allows managing rotation groups with **zero effect** on planning

**Next Step**: 
Team should decide which option to pursue based on business needs.

---

**Investigation completed by**: GitHub Copilot Agent  
**Commit**: 19f8092
