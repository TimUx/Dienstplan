# Bug Fix Summary: Lehrgang Hours Not Calculated in Statistics

## Problem Report

User reported that employee Stefanie Klein showed **168.0h (21 Schichten)** in the statistics for January 2026, when it should have shown **224.0h**.

The schedule showed 7 days marked with "L" (Lehrgang/Training) from Jan 12-18:
```
Stefanie Klein (PN012): F F F  N N N S S N  L L L L L L L F F F F F N  F F F F F N
```

### Expected Calculation
- Initial: 27 shifts × 8h = 216h
- Lehrgang period: 7 days (Jan 12-18)
- Shifts removed: 6 shifts = -48h
- Lehrgang hours to add: 7 days × 8h = +56h
- **Expected total: 216 - 48 + 56 = 224h**
- **Actual shown: 168h** ❌

## Root Cause

### Type Mismatch Between Database Schema and Query

**Database Schema (db_init.py):**
```sql
CREATE TABLE Absences (
    ...
    Type INTEGER NOT NULL,  -- Stores as INTEGER!
    ...
)
```

**Type Mapping:**
- `1` = AU (Arbeitsunfähigkeit / Sick Leave)
- `2` = U (Urlaub / Vacation)  
- `3` = L (Lehrgang / Training)

**Statistics Query (web_api.py line 4880 - BEFORE FIX):**
```sql
WHERE a.Type = 'L'  -- ❌ Checking for STRING never matches INTEGER column!
```

This meant:
- Absences were correctly created with `Type = 3`
- Schedule correctly showed "L" markers
- Shifts were correctly removed
- But statistics query **never found any Lehrgang absences** to count

Result: Only shift hours (168h) were counted, Lehrgang hours (56h) were missing.

## Solution

### Changed Query to Use Integer Value

**web_api.py line 4880 (AFTER FIX):**
```python
# Note: Type is stored as INTEGER in database: 1=AU, 2=U, 3=L
cursor.execute("""
    SELECT a.EmployeeId,
           SUM(...) * 8.0 as LehrgangHours
    FROM Absences a
    WHERE a.Type = 3  -- ✅ Now correctly matches Lehrgang type
      AND ((a.StartDate <= ? AND a.EndDate >= ?)
        OR (a.StartDate >= ? AND a.StartDate <= ?))
    GROUP BY a.EmployeeId
""", ...)
```

## Testing

### Updated Test Files

Both test files were using string values (e.g., `AbsenceType.L.value = "L"`) which SQLite silently converted to 0 in INTEGER columns. Updated to use correct integer constants:

**test_lehrgang_statistics.py:**
```python
ABSENCE_TYPE_AU = 1  # Arbeitsunfähigkeit (Sick leave)
ABSENCE_TYPE_U = 2   # Urlaub (Vacation)
ABSENCE_TYPE_L = 3   # Lehrgang (Training)
```

### Test Results - All Pass ✅

**Test 1: test_lehrgang_statistics.py**
- AU (sick): Shifts removed, hours NOT counted ✅
- U (vacation): Shifts removed, hours NOT counted ✅
- L (training): Shifts removed, 8h/day STILL counted ✅

**Test 2: test_lehrgang_scenario.py**
```
Initial:    27 shifts = 216h
Removed:    6 shifts  = -48h  
Lehrgang:   7 days    = +56h
Expected:   224h
Actual:     224h ✅
```

## Impact

### Before Fix
```
Stefanie Klein: 168.0h (21 Schichten)
```
Only shift hours counted, missing 56h from 7 Lehrgang days.

### After Fix
```
Stefanie Klein: 224.0h (21 Schichten)
```
Correctly shows: 168h (shifts) + 56h (Lehrgang) = 224h

## Files Changed

1. **web_api.py** (line 4880)
   - Changed `WHERE a.Type = 'L'` to `WHERE a.Type = 3`
   - Added comment documenting integer mapping

2. **test_lehrgang_statistics.py**
   - Added integer constants for absence types
   - Updated INSERT statements to use integers
   - Updated SELECT queries to check `Type = 3`

3. **test_lehrgang_scenario.py**
   - Added integer constants for absence types
   - Updated INSERT statements to use integers
   - Updated SELECT queries to check `Type = 3`

## Security

✅ **CodeQL Analysis:** 0 vulnerabilities found

The fix uses:
- Parameterized SQL queries (prevents SQL injection)
- Integer comparison (safer than string comparison)
- No sensitive data exposed

## Deployment Notes

### What Changed
- Only ONE line in production code (`web_api.py` line 4880)
- Change is backward compatible (absences already stored as integers)
- No database migration needed
- No frontend changes needed

### Verification Steps
1. Deploy updated `web_api.py`
2. Clear browser cache (Ctrl+Shift+Delete)
3. Navigate to Statistics page
4. Set date range: 01.01.2026 - 31.01.2026
5. Verify Stefanie Klein shows **224.0h** instead of 168.0h

### Expected Changes
All employees with Lehrgang absences will now show correct hours:
- **Before:** Only shift hours counted
- **After:** Shift hours + (Lehrgang days × 8h) counted

## Additional Context

### Why This Bug Existed

The codebase has mixed usage of string and integer for absence types:
- **Database:** Stores as INTEGER (1, 2, 3)
- **Frontend:** Uses INTEGER constants and converts to strings for display
- **Python Enum:** Uses STRING values ("AU", "U", "L") for convenience
- **Backend mapping function:** Converts INTEGER → STRING for display

The statistics query was written assuming STRING type values, but the database schema uses INTEGER. The mismatch went undetected because:
1. SQLite is loosely typed (allows strings in integer columns)
2. Tests were using enum string values that SQLite converted to 0
3. The query silently returned no results (empty set) rather than an error

### Prevention

Going forward:
- ✅ Tests now use correct integer values
- ✅ Comments document the integer mapping
- ✅ All queries reviewed to use integers

## Summary

**Bug:** Lehrgang hours not included in statistics (Type mismatch: string vs integer)  
**Fix:** Changed query to use `Type = 3` instead of `Type = 'L'`  
**Impact:** Statistics now correctly show Lehrgang days as 8h/day  
**Testing:** All tests pass, 0 security vulnerabilities  
**Result:** Stefanie Klein: 168h → 224h ✅
