# February 2026 Planning Fix - Detailed Documentation

## Problem Statement

When attempting to plan February 2026 after successfully planning January 2026, the shift planning system fails with an INFEASIBLE error, showing many warnings about conflicting locked shifts.

### Error Symptoms
```
Fehler beim Planen der Schichten:
Planung für 01.02.2026 bis 28.02.2026 nicht möglich.

WARNING: Skipping conflicting locked shift for team 2, week 0
  Existing: N, Attempted: F (from employee 7 on 2026-01-26)
[... many similar warnings ...]

✗ INFEASIBLE - No solution exists!
```

### Root Cause Analysis

#### Date Calculations
- **February 2026**: Starts Sunday Feb 1, ends Saturday Feb 28 (28 days)
- **Extended to complete weeks**: Monday Jan 26 to Sunday Mar 1 (35 days)
- **Overlapping period**: Jan 26-31 (6 days from January)

#### The Conflict

1. **January Planning (already completed)**:
   - January extended period: Dec 29, 2025 - Feb 1, 2026
   - Each employee has their individual shift assignments for Jan 26-31
   - These assignments are saved to the database

2. **February Planning (fails)**:
   - February extended period: Jan 26, 2026 - Mar 1, 2026
   - System loads existing shifts from Jan 26-31 as `locked_employee_shift`
   - Attempts to convert these to `locked_team_shift` constraints
   - **Problem**: Different team members have different shifts for the overlapping week
   - Example: Employee 7 (Team 2) has "N" on Jan 26, Employee 8 (Team 2) has "F" on Jan 26
   - Both try to lock Team 2 to different shifts → CONFLICT → INFEASIBLE

#### Why This Happens

The team rotation system (F→N→S) requires all team members to have the same shift during a week. When planning a month:
- For complete weeks within the month: All team members work together
- For partial weeks at month boundaries: Team members may work different days

When loading locked shifts from an adjacent month's partial week, the system incorrectly assumes all team members had the same shift, but they actually worked different days.

## Solution

### Code Change

**File**: `model.py`  
**Location**: Lines 204-208 (in `_apply_locked_assignments` method)

```python
# Additionally, we need to ensure the team has the correct shift for this date
# CRITICAL FIX: Only convert employee locks to team locks for dates WITHIN the original planning period
# Dates in the extended period (from adjacent months) should not create team-level locks
# because different team members may have worked different days during partial weeks
if d < self.original_start_date or d > self.original_end_date:
    # This date is in the extended portion (adjacent month)
    # Don't convert to team lock - employee lock is sufficient
    continue
```

### How It Works

1. **Employee-level locks**: Still enforced for ALL dates (including extended period)
   - Prevents double shifts for individual employees
   - Ensures employees who already worked Jan 26-31 aren't assigned again

2. **Team-level locks**: Only created for dates WITHIN the target month
   - Feb 1-28 for February planning
   - Prevents conflicts from partial weeks in adjacent months
   - Team-level locks for adjacent months are handled separately (web_api.py lines 2708-2758)

### Why This Works

- **Prevents conflicts**: No attempt to create incompatible team locks from partial weeks
- **Maintains integrity**: Employee-level locks still prevent double assignments
- **Allows planning**: Model becomes FEASIBLE because constraints don't conflict
- **Minimal changes**: Only affects lock conversion logic, not core planning algorithm

## Testing

### Test Coverage

1. **test_february_2026_conflict_fix.py**
   - Simulates the exact scenario from the problem statement
   - Plans January 2026, then February 2026 with locked shifts
   - ✅ Both plans succeed

2. **test_january_february_2026.py**
   - Full sequential planning test
   - ✅ January plans successfully
   - ✅ February plans successfully with locked shifts from January

3. **test_locked_employee_shift.py**
   - Verifies employee-level locks still work correctly
   - ✅ Locked employees respect constraints

4. **test_locked_team_shift_update.py**
   - Verifies team-level locks are created for dates within planning period
   - ✅ Team locks work correctly for target month dates

5. **Month transition tests**
   - test_duplicate_shift_bug.py: ✅ No duplicate shifts
   - test_month_transition_fix.py: ✅ Month boundaries handled correctly
   - test_cross_month_continuity.py: ✅ Planning succeeds (minor rotation differences expected)

### Test Results Summary
All tests pass. The fix successfully resolves the INFEASIBLE error while maintaining:
- No double shifts
- No regressions in existing functionality
- Clean separation between employee and team-level constraints

## Impact Analysis

### What Changed
- Team-level lock conversion skipped for dates outside original planning period
- Only affects months that have already been planned (locked shifts scenario)

### What Stayed The Same
- Employee-level locks work exactly as before
- Team-level locks within the planning month work as before
- Core planning algorithm unchanged
- All constraints and objectives unchanged

### Edge Cases Handled
- ✅ First month of the year (no previous month)
- ✅ Last month of the year (no next month)
- ✅ Partial weeks at start of month
- ✅ Partial weeks at end of month
- ✅ Months with different numbers of days
- ✅ Teams with different numbers of members

## User Impact

### Before Fix
- ❌ Planning fails after first month with INFEASIBLE error
- ❌ Must manually delete previous month's shifts to plan next month
- ❌ Loses data and continuity

### After Fix
- ✅ Can plan months sequentially without errors
- ✅ Locked shifts from previous months are respected
- ✅ No manual intervention required
- ✅ Data continuity maintained

## Related Issues and Fixes

This fix is related to several previous fixes for month boundary handling:
- **CROSS_MONTH_FIX.md**: Initial fix for cross-month continuity
- **FEBRUARY_2026_CONFLICT_FIX.md**: Detection of the conflict issue
- **FEBRUARY_2026_FIX.md**: Previous iteration of the fix

This fix supersedes the previous approaches by addressing the root cause: preventing team-level lock conversion for dates outside the original planning period.

## Technical Details

### Data Flow

1. **User initiates planning**: Feb 1-28, 2026
2. **System extends dates**: Jan 26 - Mar 1, 2026 (complete weeks)
3. **web_api.py loads locked shifts**: Lines 2686-2706
   ```python
   # Query ALL existing shift assignments in the extended planning period
   cursor.execute("""
       SELECT sa.EmployeeId, sa.Date, st.Code
       FROM ShiftAssignments sa
       WHERE sa.Date >= ? AND sa.Date <= ?
   """, (extended_start, extended_end))
   ```
4. **model.py processes locks**: Lines 184-231
   - OLD: Convert ALL employee locks to team locks → CONFLICT
   - NEW: Skip conversion for dates outside original period → NO CONFLICT

### Key Variables

- `original_start_date`: Feb 1, 2026 (user-requested start)
- `original_end_date`: Feb 28, 2026 (user-requested end)
- `start_date`: Jan 26, 2026 (extended to Monday)
- `end_date`: Mar 1, 2026 (extended to Sunday)
- `locked_employee_shift`: Dict of (employee_id, date) → shift_code
- `locked_team_shift`: Dict of (team_id, week_idx) → shift_code

### Constraint Types

1. **Hard constraints** (must be satisfied):
   - Exactly one shift per team per week
   - Team rotation (F→N→S)
   - Rest time (11 hours minimum)
   - Employee-shift linkage

2. **Soft constraints** (optimized):
   - Working hours targets
   - Maximum consecutive shifts
   - Fairness (hours, weekends, nights)
   - Staffing levels (max is soft)

The fix affects how hard constraints are generated, preventing conflicting constraints that make the model unsolvable.

## Conclusion

This fix resolves the February 2026 planning failure by preventing the creation of conflicting team-level lock constraints for weeks that span month boundaries. The solution is minimal, targeted, and preserves all existing functionality while enabling sequential month planning.

### Success Criteria Met
- ✅ February 2026 plans successfully after January
- ✅ No double shifts
- ✅ No data loss
- ✅ All existing tests pass
- ✅ No security vulnerabilities introduced
- ✅ Minimal code changes (8 lines added)
