# Max Consecutive Days Constraint Fix

## Problem Statement

The shift planning system was not properly enforcing the "max consecutive days per shift type" rule. Schedules were generated with employees working 6 consecutive night shifts (N), despite the configured maximum of 3 consecutive days for night shifts.

Example from user report:
- Anna Schmidt (PN002): Assigned N shifts on days 9-14 (6 consecutive days)
- Night shift rule: Max 3 consecutive days
- Expected: Violations should be detected and penalized
- Actual: No violations detected, allowing improper schedules

## Root Cause

Bug in `add_consecutive_shifts_constraints()` function in `constraints.py` (lines 2509-2515).

### The Issue

When checking consecutive days for a shift type, the function builds a list called `shift_indicators` containing BoolVars representing whether an employee works that shift on each day.

**Problem Code:**
```python
if shift_vars:
    is_shift = model.NewBoolVar(f"is_{shift_code}_{emp.id}_{date_idx}")
    model.Add(sum(shift_vars) >= 1).OnlyEnforceIf(is_shift)
    model.Add(sum(shift_vars) == 0).OnlyEnforceIf(is_shift.Not())
    shift_indicators.append(is_shift)
else:
    shift_indicators.append(0)  # ❌ BUG: Appending literal integer 0
```

When `shift_vars` is empty (no potential shifts for that day), the code appended a literal integer `0` instead of a BoolVar. This broke the constraint logic because:

1. CP-SAT solver requires all elements in constraints to be proper BoolVars
2. Mixing literal integers with BoolVars causes the constraint to not trigger properly
3. The violation detection at lines 2524-2526 became unreliable

### Why shift_vars Can Be Empty

The `shift_vars` list can be empty when:
- Employee doesn't have `employee_active` variable for that day
- Team's shift assignment variables don't exist for that week/shift combination
- No cross-team assignments exist for that employee/day/shift

This commonly happens across week boundaries or when team schedules change.

## The Fix

Replace the literal `0` with a BoolVar constrained to always be 0:

```python
if shift_vars:
    is_shift = model.NewBoolVar(f"is_{shift_code}_{emp.id}_{date_idx}")
    model.Add(sum(shift_vars) >= 1).OnlyEnforceIf(is_shift)
    model.Add(sum(shift_vars) == 0).OnlyEnforceIf(is_shift.Not())
    shift_indicators.append(is_shift)
else:
    # Create a BoolVar constrained to 0 instead of appending literal 0
    # This ensures all elements in shift_indicators are BoolVars for proper CP-SAT constraint handling
    zero_var = model.NewBoolVar(f"zero_{shift_code}_{emp.id}_{date_idx}")
    model.Add(zero_var == 0)  # Force it to always be 0
    shift_indicators.append(zero_var)
```

### Why This Works

1. All elements in `shift_indicators` are now proper BoolVars
2. CP-SAT can properly track and sum these variables
3. Violation detection works correctly: `sum(shift_indicators) == max_consecutive_days + 1`
4. Penalties are properly calculated when violations occur

## Testing

### Test 1: Existing Unit Test
**File:** `test_max_consecutive_days.py`
**Result:** ✅ PASS
- Verifies shift type settings are correct
- Confirms constraint logic handles different scenarios

### Test 2: New Integration Test
**File:** `test_consecutive_days_fix.py`
**Result:** ✅ PASS

#### Scenario 1: Violation Detection
- Employee works 6 consecutive night shifts (days 8-13)
- Night shift max: 3 consecutive days
- **Expected:** 2+ violations detected
- **Result:** 2 violations detected, 800 penalty points (400 each)

#### Scenario 2: No False Positives
- Employee works 3 N shifts, then switches to F shifts
- **Expected:** No violations (switching shift types is allowed)
- **Result:** 0 violations, 0 penalty points

### Test 3: Real Scenario Test
**File:** `test_real_scenario.py`
**Result:** ✅ PASS
- No regressions in existing functionality
- Conflict handling still works correctly

## Impact

### Before Fix
- ❌ Employees could be assigned 4+ consecutive night shifts
- ❌ Violations were silently ignored
- ❌ Schedules violated health and safety rules

### After Fix
- ✅ Violations properly detected and penalized
- ✅ Solver discourages excessive consecutive night shifts
- ✅ Schedules respect max consecutive days per shift type

## Code Review & Security

- **Code Review:** ✅ No issues found
- **Security Scan:** ✅ No vulnerabilities detected

## Deployment Notes

1. This is a bug fix with no breaking changes
2. No database migrations required
3. No configuration changes needed
4. Existing schedules are not affected
5. New schedules will properly enforce the constraints

## Related Documentation

- `SHIFT_TYPE_MAX_CONSECUTIVE_DAYS.md` - Original feature documentation
- `test_max_consecutive_days.py` - Unit tests for shift type settings
- `test_consecutive_days_fix.py` - Integration tests for the fix

## Date

Fix implemented: 2026-02-06
