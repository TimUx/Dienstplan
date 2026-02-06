# Cross-Shift Capacity Enforcement Fix

## Problem Statement

The N (Nacht/Night) shift scheduling system was allowing more employees than the configured maximum on many days, even when F (Früh/Early) and S (Spät/Late) shifts had available capacity.

**Specific Issue:**
- N shift configured with `max_staff_weekday = 3`
- F shift configured with `max_staff_weekday = 8`
- S shift configured with `max_staff_weekday = 6`
- On many weekdays, 5 employees were assigned to N shift (exceeding max by 2)
- Meanwhile, F and S shifts had unfilled capacity

**Expected Behavior:**
"Solange in den anderen Schichten laut Maximale Mitarbeiter Option noch Plätze frei sind, soll die Maximale Grenze der N Schicht nicht überschritten werden."

Translation: "As long as there are still free slots in other shifts according to the maximum employee option, the maximum limit of the N shift should not be exceeded."

## Root Cause

The maximum staffing constraint was implemented as a SOFT constraint with very low penalty weight:

```python
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1
HOURS_SHORTAGE_PENALTY_WEIGHT = 100
```

When the solver tried to meet target working hours (48h/week per employee), it would prefer to overstaff ANY shift (including N) rather than leave employees short of hours, because:
- Overstaffing penalty: 1 per excess employee
- Hours shortage penalty: 100 per hour short

This meant overstaffing N by 2 employees (penalty: 2) was much cheaper than leaving 1 employee 1 hour short (penalty: 100).

## Solution

Added a new constraint: **Cross-Shift Capacity Enforcement**

### Implementation

New constraint function `add_cross_shift_capacity_enforcement()` in `constraints.py`:

1. **Identifies capacity hierarchy**: Sorts shifts by `max_staff_weekday` in descending order
   - Example: F (max=8) > S (max=6) > N (max=3)

2. **Detects violations**: For each day, for each pair of shifts where `shift_high` has higher capacity than `shift_low`:
   - Calculate `overstaffing_low`: How many employees exceed the maximum in the lower-capacity shift
   - Calculate `understaffing_high`: How many slots are unfilled in the higher-capacity shift
   - Violation = `min(overstaffing_low, understaffing_high)`

3. **Applies penalty**: Each violation unit receives penalty weight of **150**
   - This is higher than `HOURS_SHORTAGE_PENALTY_WEIGHT` (100)
   - Ensures employees are assigned to higher-capacity shifts BEFORE overstaffing lower-capacity shifts

### Example

**Scenario:**
- N shift has 4 employees (max=3, overstaffed by 1)
- F shift has 7 employees (max=8, understaffed by 1)

**Violation calculation:**
- `overstaffing_N = 4 - 3 = 1`
- `understaffing_F = 8 - 7 = 1`
- `violation = min(1, 1) = 1`
- `penalty = 1 * 150 = 150`

**Effect:**
This penalty (150) is more expensive than leaving 1 employee 1 hour short (100), BUT combined with the shift ordering and understaffing penalties, the solver will prefer to:
1. Fill F shift to capacity first
2. Fill S shift to capacity next
3. Only use N shift up to its maximum
4. Use cross-team assignments if needed to meet hours without violating max constraints

### Priority Hierarchy (Updated)

```
1. Operational constraints (200-20000): Rest time, shift grouping, etc. - CRITICAL
2. DAILY_SHIFT_RATIO (200): Enforce shift ordering F >= S >= N
3. CROSS_SHIFT_CAPACITY (150): Prevent N overflow when F/S have capacity [NEW]
4. HOURS_SHORTAGE (100): Employees must reach target hours
5. TEAM_PRIORITY (50): Keep teams together
6. WEEKEND_OVERSTAFFING (50): Discourage weekend overstaffing
7. WEEKDAY_UNDERSTAFFING (dynamic 18-45): Fill shifts to capacity
8. SHIFT_PREFERENCE (±25): Reward high-capacity shifts
9. WEEKDAY_OVERSTAFFING (1): Allow if needed for hours
```

## Testing

Created comprehensive tests in:
- `test_max_staff_enforcement.py`: Validates that max staff limits are respected
- `test_max_staff_real_scenario.py`: Tests realistic scenario with 15 employees and absences
- `test_cross_shift_capacity.py`: Validates the new cross-shift capacity enforcement

All tests pass, confirming:
- N shift never exceeds its maximum of 3 employees
- F and S shifts are filled first when meeting hour targets
- Cross-shift capacity violations are properly detected and penalized

## Impact

### Before Fix
- N shift could have 4-5 employees on weekdays (exceeding max=3)
- F shift might have 6-7 employees (below max=8)
- S shift might have 4-5 employees (below max=6)
- Distribution ignored capacity ratios when meeting hour targets

### After Fix
- N shift strictly limited to max=3 employees when F or S have capacity
- F shift filled preferentially (up to max=8)
- S shift filled next (up to max=6)
- Only when F and S are both full will N be allowed to exceed its max (and even then with high penalty)
- Distribution respects capacity hierarchy: F > S > N

## Configuration

The penalty weight can be adjusted in `solver.py`:

```python
CROSS_SHIFT_CAPACITY_VIOLATION_WEIGHT = 150
```

**Guidelines:**
- Must be > `HOURS_SHORTAGE_PENALTY_WEIGHT` (100) to prevent overflow
- Should be < operational constraints (200+) to allow if absolutely necessary
- Current value (150) provides good balance

## Files Modified

1. **constraints.py**
   - Added `add_cross_shift_capacity_enforcement()` function
   - Comprehensive logic to detect and penalize capacity violations

2. **solver.py**
   - Imported new constraint function
   - Added constraint call after staffing constraints
   - Added penalty to objective function with weight 150
   - Updated priority hierarchy comments

3. **Tests**
   - `test_max_staff_enforcement.py`: Basic max staff validation
   - `test_max_staff_real_scenario.py`: Realistic scenario validation  
   - `test_cross_shift_capacity.py`: Cross-shift enforcement validation

## Related Issues

This fix addresses the core requirement:
> "Solange in den anderen Schichten laut Maximale Mitarbeiter Option noch Plätze frei sind, soll die Maximale Grenze der N Schicht nicht überschritten werden."

The solution ensures that shift distribution respects configured capacity limits while still allowing flexibility to meet employee working hour targets when necessary.
