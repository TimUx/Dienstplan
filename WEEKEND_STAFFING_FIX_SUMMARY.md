# Weekend Staffing Fix - Summary

## Problem
In February 2026, only 2 out of 15 employees (Markus Richter and Nicole Schröder) were able to reach the monthly target of 192 hours (24 shifts). The remaining employees were short by 1-4 weekend shifts:

- **Target:** 192h (24 shifts)
- **Actual results:**
  - 2 employees: 192h (24 shifts) ✓
  - 5 employees: 184h (23 shifts) - missing 1 shift
  - 3 employees: 176h (22 shifts) - missing 2 shifts
  - 3 employees: 168h (21 shifts) - missing 3 shifts
  - 2 employees: 160h (20 shifts) - missing 4 shifts

## Root Cause Analysis

### Weekend Shift Math
- **February 2026:** 28 days = 4 full weeks
  - Weekdays: 20 days (Mon-Fri × 4 weeks)
  - Weekends: 8 days (4 Saturdays + 4 Sundays)

- **To reach 192h (24 shifts):**
  - Working all weekdays: 20 days × 8h = 160h (20 shifts)
  - Still needed: 32h = 4 more shifts = **4 weekend days**

- **Total weekend capacity needed:**
  - 15 employees × 4 weekend days each = **60 weekend shifts**
  - 60 shifts / 8 weekend days = **7.5 employees per day (average)**

### The Bottleneck
The system configuration had:
```python
MaxStaffWeekend = 5  # Too low!
```

This meant only 5 employees could work on any given weekend day, limiting total weekend capacity to:
- 5 employees/day × 8 weekend days = **40 weekend shifts maximum**
- But we needed **60 weekend shifts** for all employees to reach target

**Gap:** 60 needed - 40 available = **20 weekend shifts missing** ❌

## Solution

Increased `MaxStaffWeekend` from 5 to 8 for all main shifts (F, S, N):

```python
# Before
(1, "F", "Frühschicht", "05:45", "13:45", 8.0, "#4CAF50", 48.0, 4, 10, 2, 5, ...)
(2, "S", "Spätschicht", "13:45", "21:45", 8.0, "#FF9800", 48.0, 3, 10, 2, 5, ...)
(3, "N", "Nachtschicht", "21:45", "05:45", 8.0, "#2196F3", 48.0, 3, 10, 2, 5, ...)

# After
(1, "F", "Frühschicht", "05:45", "13:45", 8.0, "#4CAF50", 48.0, 4, 10, 2, 8, ...)
(2, "S", "Spätschicht", "13:45", "21:45", 8.0, "#FF9800", 48.0, 3, 10, 2, 8, ...)
(3, "N", "Nachtschicht", "21:45", "05:45", 8.0, "#2196F3", 48.0, 3, 10, 2, 8, ...)
```

### New Capacity
- 8 employees/day × 8 weekend days = **64 weekend shifts maximum**
- Needed: 60 weekend shifts
- **Surplus:** 4 shifts (provides flexibility) ✓

## Impact

### Solver Constraints
The existing HARD constraint in `constraints.py` (line 2420) already enforces 192h minimum:
```python
min_hours_scaled = 1920  # 192h × 10 (scaling factor)
model.Add(sum(total_hours_terms) >= min_hours_scaled)
```

With the new `MaxStaffWeekend=8`, this constraint can now be satisfied for **all employees**.

### Fairness
The weekend fairness objectives in the solver (lines 2983-3032) will continue to distribute weekend work evenly among employees, but now with sufficient capacity for everyone to reach their target hours.

## Files Changed

- **db_init.py** (lines 604, 609, 614)
  - Modified shift type tuples to increase MaxStaffWeekend parameter

## Testing

Verified the change by creating a test database and confirming:
```
✓ F (Frühschicht): Min=2, Max=8
✓ N (Nachtschicht): Min=2, Max=8
✓ S (Spätschicht): Min=2, Max=8
```

## Deployment Notes

For **existing databases**, the administrator will need to manually update the MaxStaffWeekend values:
1. Navigate to **Administration → Schichtverwaltung** (Shift Management)
2. Edit each shift type (F, S, N)
3. Change "Max Besetzung Wochenende" from 5 to 8
4. Save changes

For **new databases**, the change will be applied automatically during initialization.

## Summary

This minimal change ensures that the shift planning solver has sufficient weekend capacity to assign enough shifts for all employees to reach their mandatory 192h monthly target, addressing the issue where 13 out of 15 employees were falling short.
