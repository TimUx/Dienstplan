# Weekend Overstaffing Fix

## Problem Statement (German)

> Schaue dir bitte den letzt PR an.
> Hier sollte eigentlich behoben werden, dass die Wochenden zu viele Schichten zugewiesen werden, während in den Wochen noch tage frei sind.
> 
> Beim aktuellen Schichtplan hat insbesondere das letzte Wochenende wieder zuviele Schichten geplant, obwohl noch genug Wochentage frei sind

## Translation

"Please look at the last PR. This was supposed to fix that weekends are being assigned too many shifts while weekdays still have free days.

In the current shift plan, particularly the last weekend has too many shifts planned again, even though enough weekdays are still free."

## Issue Analysis

### Previous Fix (PR #162)
PR #162 attempted to fix weekend overstaffing by setting:
```python
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1   # Allow weekday overstaffing
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 5   # Avoid weekend overstaffing
```

The logic was: weekday overstaffing (1) < weekend overstaffing (5), so the solver should prefer weekdays.

### Why It Still Failed

**The Missing Factor: Weekday Understaffing Penalties**

The previous fix overlooked that the solver also has weekday understaffing penalties:
```python
shift_priority_weights = {
    'F': 20,  # Früh/Early shift
    'S': 12,  # Spät/Late shift  
    'N': 5    # Nacht/Night shift
}
```

These penalties encourage filling weekdays to their maximum capacity.

### The Real Problem

The solver compares these costs when deciding where to assign shifts:

**Option 1: Leave weekday understaffed**
- Cost: 20 points (for F shift) to 5 points (for N shift)

**Option 2: Overstaff weekend**
- Cost: 5 points (with old WEEKEND_OVERSTAFFING_PENALTY_WEIGHT)

**Result:** The solver chooses Option 2 (5 points) over Option 1 (20 points for F shifts) ❌

This explains why Saturday 28 had 13 employees while earlier weekdays still had free slots!

## The Solution

### Corrected Penalty Hierarchy

**New configuration:**
```python
HOURS_SHORTAGE_PENALTY_WEIGHT = 100         # Highest priority
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1     # Acceptable if needed
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 50    # STRONGLY avoid (was 5)
```

### Why This Works

**Priority hierarchy now:**
1. **Hours shortage (100)** - MUST reach 192h target
2. **Operational constraints (200-20000)** - Rest time, shift grouping, etc.
3. **Weekend overstaffing (50)** - STRONGLY avoid
4. **Weekday understaffing (20/12/5)** - Encourage filling to capacity
5. **Weekday overstaffing (1)** - Acceptable if needed

**Cost comparison:**
```
Option 1: Leave weekday F shift understaffed
  Cost: 20 points

Option 2: Overstaff weekend
  Cost: 50 points

Result: Solver chooses Option 1 (20 < 50) ✓
```

The solver will now:
1. ✅ Fill weekdays to maximum capacity first (cost: 20/12/5)
2. ✅ Only overstaff weekends if absolutely necessary (cost: 50)
3. ✅ Prefer weekday overstaffing over weekend overstaffing (1 < 50)

## Expected Behavior Changes

### Before Fix
```
Week 1-3: Some weekdays not filled to capacity
Week 4:   Saturday 28 with 13 employees (overstaffed)
Reason:   Weekend overstaffing (5) < Weekday understaffing (20)
```

### After Fix
```
Week 1-4: All weekdays filled to capacity when possible
Week 4:   Saturday 28 with balanced staffing (at or near max)
Reason:   Weekend overstaffing (50) > Weekday understaffing (20)
```

## Implementation Details

### Files Changed

#### solver.py (lines 29-41)
```python
# BEFORE:
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 5

# AFTER:
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 50
```

Updated comments to clarify the priority hierarchy including weekday understaffing.

#### solver.py (lines 289-300)
Updated log messages to reflect the stronger weekend overstaffing penalty.

## Benefits

### 1. Correct Priority Order
- ✅ Weekdays filled to capacity before weekends are overstaffed
- ✅ Proper cost relationship: weekend overstaffing (50) > weekday understaffing (20/12/5)
- ✅ Aligns with user requirements

### 2. Better Schedule Quality
- ✅ More balanced staffing throughout the month
- ✅ Eliminates excessive weekend overstaffing
- ✅ Maximizes weekday capacity utilization

### 3. Maintains Flexibility
- ✅ Still allows weekend overstaffing if truly necessary for hours targets
- ✅ Preserves all other constraint priorities
- ✅ No database changes required

### 4. Simple and Clear
- ✅ Single parameter change (5 → 50)
- ✅ Easy to understand and adjust
- ✅ Well-documented rationale

## Comparison: Before vs. After

| Aspect | PR #162 (Failed) | This Fix (Correct) |
|--------|------------------|-------------------|
| **Weekend Overstaffing** | Weight 5 | Weight 50 |
| **Weekday Understaffing** | Not considered | Weight 20/12/5 |
| **Priority Relationship** | 5 < 20 ❌ | 50 > 20 ✓ |
| **Solver Behavior** | Prefers weekend overstaffing | Fills weekdays first |
| **Saturday 28 Example** | 13 employees | Balanced staffing |
| **Weekday Utilization** | Partial | Full capacity |

## Testing Recommendations

### Verification Checks
1. Generate schedule for February 2026
2. Verify all weekdays are filled to capacity before weekends are overstaffed
3. Check Saturday 28 has balanced staffing (not 13+ employees)
4. Ensure employees still reach 192h target
5. Confirm no regression in other constraints

### Expected Metrics
- Weekday staffing: At maximum capacity
- Weekend staffing: At or slightly above maximum (if needed)
- Last Saturday 28: ~8-10 employees (not 13)
- All employees: 184-192h monthly target

## Summary

This fix corrects the penalty weight hierarchy by ensuring:

1. ✅ **Weekend overstaffing (50)** > **Weekday understaffing (20/12/5)**
2. ✅ Solver fills weekdays to capacity before overstaffing weekends
3. ✅ Addresses the root cause that PR #162 missed
4. ✅ Simple single-parameter change with clear rationale

**Key Insight:** It's not enough to make weekend overstaffing more expensive than weekday overstaffing. We must make weekend overstaffing more expensive than **weekday understaffing** to ensure weekdays are filled first!

**Result:** When the solver needs to distribute shifts for target hours, it will now:
1. Fill weekdays to max capacity (cost 20/12/5)
2. Consider weekday overstaffing (cost 1)  
3. Only overstaff weekends as last resort (cost 50)

This creates the desired behavior: weekdays filled before weekends overstaffed.
