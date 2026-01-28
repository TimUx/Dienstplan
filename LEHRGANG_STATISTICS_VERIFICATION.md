# Lehrgang Statistics Fix - Verification Report

## Problem Statement (German)
```
Es wurde für einen Monat alle Schichten geplant.
Für Mitarbeiter "A" wurde nachträglich eine Abwesenheit für einen Lehrgang für 7 Tage (Montag bis Sonntag) eingetragen.
Seine Statistik für diesen Monat zeigt 216h an.
Die bereits geplanten Schichten (6 Tage) wurden sauber entfernt.

INFO: Removed 6 shift assignment(s) for absent employee 13
      Date range: 2026-01-12 to 2026-01-18

Im Dienstplan wird richtig das "L" Kürzel angezeigt.

In der Statistik werden jetzt 168h für diesen Mitarbeiter in dem Monat angezeigt.
Gleichzeitig sollen aber Abwesenheiten für Lehrgang ("L") als 8h Tag in der Statistik für den User drauf gerechnet werden.
Sprich ein L Tag ist gleich zu setzen für ein Schichttag, für die Statistik.

Demnach hätte die Statistik anstelle 168h, 224h anzeigen müssen.
216 - 6 Tage * 8h + 7 Tage * 8h = 224h
```

## Problem Statement (English Translation)
A shift schedule was created for a month. For employee "A", a training course absence ("Lehrgang") was added retrospectively for 7 days (Monday to Sunday). His statistics showed 216h for this month. The already planned shifts (6 days) were cleanly removed.

INFO: Removed 6 shift assignment(s) for absent employee 13
      Date range: 2026-01-12 to 2026-01-18

The schedule correctly displays the "L" marker for training.

However, the statistics now show 168h for this employee in the month. But training absences ("L") should be counted as 8h/day in the statistics. In other words, an "L" day should be treated the same as a shift day for statistics purposes.

Therefore, the statistics should show 224h instead of 168h.
216 - 6 days * 8h + 7 days * 8h = 224h

## Investigation Results

### ✅ FEATURE IS ALREADY CORRECTLY IMPLEMENTED

After thorough investigation, I found that **the Lehrgang statistics feature is already correctly implemented** in the codebase.

### Code Location
File: `web_api.py`, lines 4814-4920
Endpoint: `/api/statistics/dashboard`

The implementation follows this logic:
1. **Calculate shift hours** from `ShiftAssignments` table (lines 4841-4861)
2. **Calculate Lehrgang hours separately** from `Absences` table where `Type = 'L'` (lines 4864-4916)
3. **Combine both**: `totalHours = shiftHours + lehrgangHours` (line 4920)

### Key SQL Query for Lehrgang Hours
```sql
SELECT a.EmployeeId,
       SUM(
           CASE
               WHEN a.StartDate >= ? AND a.EndDate <= ? THEN
                   julianday(a.EndDate) - julianday(a.StartDate) + 1
               -- ... other cases for date range overlaps
           END
       ) * 8.0 as LehrgangHours
FROM Absences a
WHERE a.Type = 'L'
  AND ((a.StartDate <= ? AND a.EndDate >= ?)
    OR (a.StartDate >= ? AND a.StartDate <= ?))
GROUP BY a.EmployeeId
```

This query:
- Finds all `Absences` with `Type = 'L'` (Lehrgang)
- Calculates the number of days in the date range
- Multiplies by 8.0 to get hours (8h per day)
- Handles all edge cases where the absence overlaps with the reporting period

## Test Results

### Test 1: `test_lehrgang_statistics.py` ✅ PASS
Tests all three absence types:
- **AU (sick leave)**: Shifts removed, hours NOT counted ✅
- **U (vacation)**: Shifts removed, hours NOT counted ✅
- **L (training)**: Shifts removed, but 8h/day STILL counted ✅

### Test 2: `test_lehrgang_scenario.py` ✅ PASS
Tests the EXACT scenario from the problem statement:
- Initial: 27 shifts = 216h
- Lehrgang added: Jan 12-18 (7 days)
- Shifts removed: 6 shifts = -48h
- Lehrgang hours added: 7 days × 8h = +56h
- **Expected**: 216 - 48 + 56 = 224h
- **Actual**: 224h ✅

### Test 3: API Logic Test ✅ PASS
Verified the exact SQL queries from `web_api.py`:
- Shift hours: 168h (21 shifts)
- Lehrgang hours: 56h (7 days × 8h)
- Total hours: 224h ✅

## Documentation

The feature is documented in:
- `ABSENCE_SHIFT_REMOVAL_FIX.md` - Comprehensive documentation of the fix
- Comments in `web_api.py` (lines 4836-4838)

## Conclusion

**The reported issue is already fixed in the current codebase.** All tests pass and confirm that:

1. ✅ Shifts are correctly removed when a Lehrgang is added
2. ✅ Lehrgang days are counted as 8h/day in statistics
3. ✅ The calculation produces the correct result: 224h (not 168h)

### Possible Reasons for Original Issue Report

1. **Timing**: The issue was reported before the fix was merged (PR #133)
2. **Caching**: The user might be seeing cached statistics data
3. **Deployment**: The fix might not be deployed to the user's environment yet
4. **Browser Cache**: The frontend might have cached old statistics

### Recommendations

1. ✅ Clear browser cache and refresh the statistics page
2. ✅ Verify the deployment is using the latest code (after PR #133)
3. ✅ Check that the database has the correct absence type 'L' set
4. ✅ Verify the statistics endpoint is being called with correct date ranges

## Files Involved

- ✅ `web_api.py` - Main statistics calculation (already correct)
- ✅ `test_lehrgang_statistics.py` - Comprehensive test (already exists, passes)
- ✅ `test_lehrgang_scenario.py` - New test matching exact problem scenario (passes)
- ✅ `ABSENCE_SHIFT_REMOVAL_FIX.md` - Documentation (already exists)

## Summary

**No code changes are required.** The feature works correctly as implemented. The issue appears to be resolved.
