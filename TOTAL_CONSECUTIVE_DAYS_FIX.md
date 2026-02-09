# Total Consecutive Working Days Constraint

## Overview

This document describes the enhancement to the consecutive working days constraint that prevents employees from working excessive consecutive days across different shift type combinations.

## Problem Statement

The previous implementation had a gap that allowed employees to work too many consecutive days when switching between shift types, even when individual shift type limits were respected.

### Example Scenario

Given:
- S shift (Spätschicht): `max_consecutive_days = 6`
- N shift (Nachtschicht): `max_consecutive_days = 3`

**Problematic schedule:**
```
Days: S S S S S N N N
      1 2 3 4 5 6 7 8
```

Previous behavior:
- S check: 5 consecutive S days < 6 limit ✓ (no violation)
- N check: 3 consecutive N days = 3 limit ✓ (no violation)
- **Total: 8 consecutive working days with NO REST ❌ (not detected)**

This violated the intent that employees should have regular rest periods, as working 8 days straight is excessive regardless of shift type combinations.

## Solution

Added a **Total Consecutive Working Days Constraint** that enforces a maximum number of consecutive working days across ALL shift types, not just per individual shift type.

### Implementation Details

The constraint uses the **maximum** of all shift types' `max_consecutive_days` values as the global limit. For example:
- F shift: `max_consecutive_days = 6`
- S shift: `max_consecutive_days = 6`
- N shift: `max_consecutive_days = 3`
- **Total limit: max(6, 6, 3) = 6 days**

This ensures that:
1. Employees cannot work more than 6 consecutive days regardless of shift combinations
2. The limit respects the most permissive shift type setting
3. Shift type switching is still allowed within the total limit

### Constraint Logic

For each employee and each sliding window of `(max_total_consecutive + 1)` days:
1. Check if employee works ANY shift on each day in the window
2. If all `(max_total_consecutive + 1)` days have work → **VIOLATION**
3. Penalty: 400 points (same priority as other consecutive constraints)

## Examples

### Scenario 1: 6x S + 2x N = 8 consecutive days
```
Schedule: S S S S S S N N
          1 2 3 4 5 6 7 8
```
- **Old behavior:** Violation only caught by cross-shift enforcement (after 6x S, must rest)
- **New behavior:** Additional violation detected by total consecutive constraint (8 > 6)
- **Result:** ❌ VIOLATION (caught by both constraints)

### Scenario 2: 5x S + 3x N = 8 consecutive days
```
Schedule: S S S S S N N N
          1 2 3 4 5 6 7 8
```
- **Old behavior:** No violation detected (5 < 6 for S, 3 = 3 for N)
- **New behavior:** Violation detected (8 > 6 total consecutive days)
- **Result:** ❌ VIOLATION (caught by new constraint) ✅ **BUG FIX**

### Scenario 3: 6x S with rest, then 2x N
```
Schedule: S S S S S S + N N
          1 2 3 4 5 6   7 8
```
- **Behavior:** No violation
- Rest day breaks the consecutive sequence
- Maximum consecutive: 6 days (S) or 2 days (N separately)
- **Result:** ✓ NO VIOLATION

### Scenario 4: 5x F + 1x rest + 5x S
```
Schedule: F F F F F + S S S S S
          1 2 3 4 5   6 7 8 9 10
```
- **Behavior:** No violation
- F: 5 consecutive < 6 ✓
- S: 5 consecutive < 6 ✓
- Rest day breaks the sequence
- **Result:** ✓ NO VIOLATION

### Scenario 5: 3x S + 3x F = 6 consecutive days
```
Schedule: S S S F F F
          1 2 3 4 5 6
```
- **Behavior:** No violation
- S: 3 consecutive < 6 ✓
- F: 3 consecutive < 6 ✓
- Total: 6 consecutive = 6 limit ✓ (at limit but not over)
- **Result:** ✓ NO VIOLATION

## Constraint Priority

All consecutive working days constraints have the same penalty weight:
- Per-shift-type consecutive: **400 points**
- Cross-shift enforcement: **400 points**
- Total consecutive (new): **400 points**

This ensures balanced enforcement across all three constraint types.

## Backward Compatibility

This change is **fully backward compatible**:
- Adds additional constraint without removing existing ones
- All existing valid schedules remain valid
- Only prevents new invalid schedules that should have been caught before
- No database schema changes required
- No configuration changes required

## Testing

### Test Script

Run the test to validate the implementation:
```bash
python3 test_total_consecutive_days.py
```

This test verifies:
- Total consecutive days limit is calculated correctly
- Violations are detected across shift type combinations
- Rest days properly reset the consecutive counter
- Existing behavior is preserved

### Existing Tests

All existing tests continue to pass:
```bash
python3 test_max_consecutive_days.py
python3 test_cross_shift_consecutive.py
```

## Benefits

1. **Improved Employee Health & Safety**: Prevents excessive consecutive working days
2. **Closes Constraint Gap**: Catches violations that were previously undetected
3. **Simple Logic**: Uses existing shift type configuration, no new settings needed
4. **Consistent Penalties**: Same priority as other consecutive constraints
5. **Clear Intent**: Maximum consecutive days means TOTAL days, not per-shift-type

## Related Issues

- Fixes the specific issue reported with Lisa Meyer's schedule
- Addresses edge cases where shift type switching led to excessive consecutive days
- Aligns with labor regulations requiring regular rest periods

## Code Changes

### Modified Files
- `constraints.py`: Added total consecutive working days constraint in `add_consecutive_shifts_constraints()`

### New Files
- `test_total_consecutive_days.py`: Test script validating the new constraint
- `TOTAL_CONSECUTIVE_DAYS_FIX.md`: This documentation file

## Future Considerations

### Configurable Total Limit

Currently, the total limit is derived from shift type settings (`max(max_consecutive_days)`). 

Future enhancement could add a separate global setting:
```python
# Example: Add to GlobalSettings table
MAXIMUM_TOTAL_CONSECUTIVE_DAYS = 6  # Independent of shift type limits
```

Benefits:
- More explicit control
- Can be stricter than any individual shift type
- Easier to adjust without changing shift type configurations

### Rest Day Recommendations

The problem statement mentions: "Zusätzlich es es auch Sinnvoll, pause Tage zwischen einen Schichtwechsel zu legen."

Translation: "Additionally, it makes sense to place rest days between shift changes."

This could be implemented as a **soft constraint** (lower priority) that encourages but doesn't require rest days when switching shift types, especially for major transitions like:
- S → F (Late to Early)
- N → F (Night to Early)

These transitions already have rest time constraints based on minimum hours between shifts, but an additional soft preference could improve schedule quality.

## Summary

The total consecutive working days constraint closes an important gap in the shift planning system, ensuring employees get proper rest periods even when working different shift types. The implementation is simple, efficient, and fully compatible with existing functionality.
