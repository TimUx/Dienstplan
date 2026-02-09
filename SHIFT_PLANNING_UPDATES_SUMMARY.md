# Shift Planning System Updates - Summary

## Overview
This document summarizes the two major changes made to the Dienstplan shift planning system to address the requirements specified in the problem statement.

## Issue 1: Cross-Shift-Type Consecutive Days Enforcement

### Problem Statement
Die Maximale aufeinanderfolgenden Schichten funktionieren aktuell anscheinend nur Schichtintern. Dies muss aber auch Schicht übergreifend berücksichtigt werden.

**Beispiel:**
- Einstellung in S Schicht = 6, F Schicht = 6, N Schicht = 3
- Mitarbeiter 1 = 6x S Schicht → 1 Tag Pause egal ob danach F oder S Schicht geplant wird
- Mitarbeiter 1 = 3x N Schicht → 1 Tag Pause, egal ob am nächsten Tag eine F oder S Schicht geplant werden würde

### Solution Implemented
Modified the `add_consecutive_shifts_constraints` function in `constraints.py` to enforce cross-shift-type limits:

**Key Changes:**
1. **Per-shift-type tracking remains**: Each shift type still has its own `max_consecutive_days` setting (e.g., N=3, F/S=6)
2. **Cross-shift-type enforcement added**: After working `max_consecutive_days` of ANY shift type, employee must have a rest day before working ANY shift (not just the same type)

**Implementation Details:**
- After N consecutive days of shift X, the system checks if employee works ANY shift on day N+1
- If yes, a penalty of 400 points is applied (same priority as per-shift-type violations)
- This ensures proper rest periods regardless of shift type changes

**Example Scenarios:**
```
Scenario 1: 6x S shift, then F shift
Days 1-6: S S S S S S (reaches max_consecutive_days=6)
Day 7:    F             ← VIOLATION: needs rest day

Scenario 2: 6x S shift, rest day, then F shift  
Days 1-6: S S S S S S (reaches max_consecutive_days=6)
Day 7:    OFF          ← Rest day
Day 8:    F            ← OK: rest day provided

Scenario 3: 3x N shift, then S shift
Days 1-3: N N N       (reaches max_consecutive_days=3)
Day 4:    S            ← VIOLATION: needs rest day

Scenario 4: 5x S shift, then F shift
Days 1-5: S S S S S   (below limit of 6)
Day 6:    F            ← OK: limit not reached yet
```

**Files Modified:**
- `constraints.py`: Added cross-shift-type enforcement logic (lines 2900-2976)
- `test_cross_shift_consecutive.py`: New test documenting scenarios
- `test_consecutive_days_fix.py`: Updated to reflect new requirement

## Issue 2: Week Start Change from Monday to Sunday

### Problem Statement
Die Arbeits- bzw Rotationswoche beginnt nicht am Montag sondern am Sonntag. Sprich die Woche geht von So - Sa und dementsprechend sind auch die Schichten für die Teams einzuplanen.

### Solution Implemented
Changed the week structure throughout the system from Monday-Sunday to Sunday-Saturday:

**Key Changes:**
1. **Week extension logic**: Planning periods are now extended to complete Sunday-Saturday weeks
2. **Week generation**: Weeks are now split at Sunday boundaries (not Monday)
3. **All week-related calculations**: Updated to use Sunday as first day (weekday=6)

**Implementation Details:**

**Before (Monday-Sunday):**
```python
# Week starts on Monday (weekday=0)
if start_date.weekday() != 0:  # Not Monday
    days_back = start_date.weekday()
    extended_start = start_date - timedelta(days=days_back)

# Week ends on Sunday (weekday=6)
if end_date.weekday() != 6:  # Not Sunday
    days_forward = 6 - end_date.weekday()
    extended_end = end_date + timedelta(days=days_forward)

# Week split at Monday
if d.weekday() == 0 and current_week:  # Monday
    weeks.append(current_week)
    current_week = []
```

**After (Sunday-Saturday):**
```python
# Week starts on Sunday (weekday=6)
if start_date.weekday() != 6:  # Not Sunday
    days_back = start_date.weekday() + 1
    extended_start = start_date - timedelta(days=days_back)

# Week ends on Saturday (weekday=5)
if end_date.weekday() != 5:  # Not Saturday
    days_forward = (5 - end_date.weekday() + 7) % 7
    extended_end = end_date + timedelta(days=days_forward)

# Week split at Sunday
if d.weekday() == 6 and current_week:  # Sunday
    weeks.append(current_week)
    current_week = []
```

**Example:**
```
March 2026 (starts Sun Mar 1, ends Tue Mar 31)

OLD (Monday-Sunday weeks):
Extended: Mon Feb 23 - Sun Apr 5
Week 0: Feb 23-Mar 1 (boundary week)
Week 1: Mar 2-8
...

NEW (Sunday-Saturday weeks):
Extended: Sun Mar 1 - Sat Apr 4
Week 0: Mar 1-7 (all in March, not boundary)
Week 1: Mar 8-14
...
Week 4: Mar 29-Apr 4 (boundary week)
```

**Files Modified:**
- `model.py`: Week extension and generation logic (lines 93-110, 343-362)
- `web_api.py`: Calendar view week calculations (lines 201-232, 2720-2730)
- `validation.py`: Week generation for validation (lines 646-661, 775-790)
- `solver.py`: Diagnostics messages (lines 913-932)
- `constraints.py`: Week reference comment (line 211)
- `test_week_start_sunday.py`: New comprehensive test
- `test_boundary_week_fix.py`: Updated expectations

## Testing

### Tests Created/Updated
1. **test_week_start_sunday.py**: New test verifying Sunday-Saturday week structure
   - Tests week extension logic
   - Tests week generation
   - Tests incomplete week boundaries
   
2. **test_cross_shift_consecutive.py**: New test documenting cross-shift-type scenarios
   - Scenario 1: 6x S → F (violation)
   - Scenario 2: 6x S → OFF → F (OK)
   - Scenario 3: 3x N → S (violation)
   - Scenario 4: 3x N → OFF → S (OK)
   - Scenario 5: 5x S → F (OK, limit not reached)
   - Scenario 6: Mixed shifts under limit (OK)

3. **test_consecutive_days_fix.py**: Updated to reflect new requirement
   - Test 1: 6 consecutive N shifts (violation)
   - Test 2: 3x N → F without break (violation, as expected)

4. **test_boundary_week_fix.py**: Updated for Sunday-Saturday weeks
   - Verifies boundary week detection
   - Tests week structure with new boundaries

### Test Results
All tests pass successfully:
- ✅ test_week_start_sunday.py
- ✅ test_cross_shift_consecutive.py  
- ✅ test_consecutive_days_fix.py
- ✅ test_boundary_week_fix.py
- ✅ test_max_consecutive_days.py

### Security Analysis
CodeQL security scan completed with **0 vulnerabilities found**.

## Code Review Feedback Addressed

### Issue: Modulo Operations
**Problem**: Unnecessary modulo operations in week calculations
**Solution**: Simplified calculations:
- `(start_date.weekday() + 1) % 7` → `start_date.weekday() + 1` (no modulo needed)
- `(5 - end_date.weekday()) % 7` → `(5 - end_date.weekday() + 7) % 7` (handles negatives properly)

### Issue: Code Duplication
**Noted**: Week calculation logic is duplicated across multiple files
**Status**: Acknowledged but not refactored in this PR to maintain minimal changes. Suggestion for future refactoring: Create utility functions in a shared module.

## Impact Analysis

### Backward Compatibility
⚠️ **Breaking Changes**: Both changes will affect existing schedules:

1. **Week boundaries**: Existing schedules using Monday-Sunday weeks will need to be regenerated
2. **Consecutive days**: Schedules that relied on shift-type switching without breaks may now show violations

### Migration Path
1. Regenerate all schedules after deploying these changes
2. Review and adjust any locked shift assignments if needed
3. Communicate the new rest period requirements to staff

## Conclusion

Both issues have been successfully implemented with comprehensive testing:

✅ **Issue 1**: Cross-shift-type consecutive days enforcement working correctly
✅ **Issue 2**: Week start changed to Sunday successfully
✅ All tests passing
✅ No security vulnerabilities
✅ Code review feedback addressed

The system now properly enforces rest periods after maximum consecutive days regardless of shift type changes, and uses Sunday-Saturday weeks for rotation planning as required.
