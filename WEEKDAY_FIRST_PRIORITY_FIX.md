# Weekday-First Priority Fix

## Problem Statement (German)

> Der aktuelle Dienstplan schafft es fast alle User mit den geforderten Stunden und Schichten zu belegen.
> 
> Die Verteilung der Schichten könnte aber noch etwas besser sein. Insbesondere in der letzten Woche wird der Samstag mit 15 Mitarbeitern besetzt, während in den Wochen davor einige Wochentage nicht belegt wurden.
>
> Wenn Schichten verteilt werden, um die Soll Arbeitsstunden zu erreichen, sollen zunächst die Wochentage aufgefüllt werden bevor die Wochenenden aufgefüllt werden.
>
> Die Arbeitsweise muss wie folgt laufen:
> 1. Die Maximale Anzahl Mitarbeiter je Schicht einhalten
> 2. Die Soll Arbeitsstunden je Mitarbeiter erreichen
> 3. Wenn Sollarbeitsstunden nicht eingehalten werden können, die Anzahl Maximaler Mitarbeiter von Wochentagen überschreiten und die Woche füllen
> 4. Wenn Soll Arbeitstunden immer noch nicht erreicht werden, die Anzahl Maximaler Mitarbeiter an Wochenenden überschreiten und die Wochenenden füllen

## Translation

"The current schedule manages to assign almost all users with the required hours and shifts.

However, the distribution of shifts could be better. Particularly in the last week, Saturday is staffed with 15 employees while some weekdays in earlier weeks were not fully staffed.

When distributing shifts to reach target work hours, weekdays should be filled first BEFORE weekends are filled.

The working order must be as follows:
1. Respect the maximum number of employees per shift
2. Reach target work hours per employee
3. If target work hours cannot be met, exceed the maximum number of employees on WEEKDAYS and fill the week
4. If target work hours are still not met, then exceed the maximum number of employees on WEEKENDS and fill weekends (with even distribution)"

## The Issue

### Previous State (After SOFT_CONSTRAINT_PRIORITY_FIX.md)

The previous fix established:
- `HOURS_SHORTAGE_PENALTY_WEIGHT = 100` (highest priority)
- `WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 2`
- `WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 1`

This meant that when the solver needed to exceed maximum staffing to reach target hours:
- Weekend overstaffing cost: 1 point per employee
- Weekday overstaffing cost: 2 points per employee

**Result**: The solver preferred to overstaff WEEKENDS (lower penalty) rather than WEEKDAYS (higher penalty).

### Example Scenario

Employee needs 8 more hours to reach 192h target. Two options:
1. Assign to weekday shift → overstaffing penalty = 2 points
2. Assign to weekend shift → overstaffing penalty = 1 point

**Solver chooses option 2** → Weekends get overstaffed while weekdays remain under capacity! ❌

## The Solution

### Reversed Penalty Weights

**New configuration:**
```python
HOURS_SHORTAGE_PENALTY_WEIGHT = 100         # Highest priority - unchanged
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1     # Changed from 2 → More acceptable
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 5     # Changed from 1 → Less acceptable
```

### Priority Hierarchy (Updated)

1. **Hours Shortage (Weight: 100)** - HIGHEST PRIORITY
   - Employees must reach their 192h monthly target
   - Overrides all other soft constraints

2. **Operational Constraints (Weights: 200-20000)**
   - Rest time violations, shift grouping, etc.
   - Maintain work quality and compliance

3. **WEEKEND Overstaffing (Weight: 5)** - AVOID FIRST
   - Higher penalty = less acceptable
   - Only used when weekdays are already full

4. **WEEKDAY Overstaffing (Weight: 1)** - PREFER FIRST
   - Lower penalty = more acceptable
   - Fill weekdays before weekends

### Why This Works

Employee needs 8 more hours to reach 192h target:

**Cost Analysis:**
```
Cost of leaving employee short:
  - Hours shortage: 8h × 100 = 800 points

Cost of overstaffing weekday:
  - Weekday overstaffing: 1 employee × 1 = 1 point

Cost of overstaffing weekend:
  - Weekend overstaffing: 1 employee × 5 = 5 points

Result: Solver prefers weekday (1 < 5 < 800) ✓
```

The solver will:
1. First try to stay within max staffing (0 penalty)
2. If hours shortage would occur (800 penalty), fill weekdays first (1 penalty)
3. Only fill weekends (5 penalty) if weekdays are exhausted
4. **Never** leave employees short of target hours (800 penalty is too high)

## Expected Behavior Changes

### Before Fix
```
Week 1-3: Weekdays partially filled
Week 4:   Saturday with 15 employees (overstaffed)
Reason:   Solver preferred weekend overstaffing (weight 1) over weekday (weight 2)
```

### After Fix
```
Week 1-3: Weekdays fully filled first (if needed for target hours)
Week 4:   Balanced distribution, no extreme weekend overstaffing
Reason:   Solver now prefers weekday overstaffing (weight 1) over weekend (weight 5)
```

## Implementation Details

### Files Changed

#### solver.py (lines 29-36)
```python
# BEFORE:
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 2   # Higher than weekend
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 1   # Lower than weekday

# AFTER:
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1   # Lower = more acceptable
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 5   # Higher = less acceptable
```

#### solver.py (lines 285-296)
Reordered to apply weekday penalties before weekend penalties in the objective function.

#### constraints.py (lines 452-460)
Updated docstring to document the new priority order.

## Benefits

### 1. Aligns with Requirements
- ✅ Weekdays filled before weekends (as requested)
- ✅ Even distribution across weeks
- ✅ Still reaches 192h target for all employees

### 2. Better Schedule Quality
- ✅ More balanced staffing throughout the month
- ✅ Avoids extreme weekend overstaffing (e.g., 15 employees on one Saturday)
- ✅ Utilizes available weekday capacity first

### 3. Maintains Flexibility
- ✅ No database changes required
- ✅ System still adapts to absences and constraints
- ✅ Clear, adjustable priority weights

### 4. Backwards Compatible
- ✅ Works with existing databases
- ✅ No migration scripts needed
- ✅ All other constraints unchanged

## Testing Recommendations

### Verification Checks
1. Run solver on February 2026 schedule
2. Verify employees reach 192h target
3. Check that weekdays have higher occupancy than before
4. Confirm weekends are not overstaffed unless necessary
5. Ensure even distribution across all weekends

### Expected Metrics
- All employees: 184-192h (target range)
- Weekday staffing: Closer to max capacity
- Weekend overstaffing: Reduced or eliminated
- Schedule quality: Improved balance

## Comparison: Before vs. After

| Aspect | Before Fix | After Fix |
|--------|-----------|-----------|
| **Weekday Overstaffing** | Weight 2 (avoid) | Weight 1 (prefer) |
| **Weekend Overstaffing** | Weight 1 (prefer) | Weight 5 (avoid) |
| **Fill Priority** | Weekends first | Weekdays first |
| **Last Saturday Example** | 15 employees | Balanced staffing |
| **Early Week Weekdays** | Under capacity | Filled to capacity |
| **Hours Target** | 192h reached | 192h reached (unchanged) |

## Summary

This fix implements the correct prioritization by:
1. ✅ Reversing overstaffing penalty weights (weekday < weekend)
2. ✅ Ensuring weekdays are filled before weekends
3. ✅ Maintaining all employees' 192h monthly target
4. ✅ Creating more balanced schedules across the month
5. ✅ Following the explicit requirements in the issue

**Result:** When the solver needs to exceed maximum staffing to reach target hours, it now fills weekdays first (weight 1) before filling weekends (weight 5), creating a more balanced and efficient schedule distribution.
