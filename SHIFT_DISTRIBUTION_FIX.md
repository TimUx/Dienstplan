# Shift Distribution Fix: Dynamic Weight Calculation

## Problem Statement

The shift planning system was using hardcoded priority weights for different shift types (F, S, N), which didn't respect the actual capacity settings configured in the database. This led to improper distribution where S (Spätschicht) was getting more assignments than F (Frühschicht), even though F has a higher maximum capacity.

### Original Issue
From user report:
- F shift should have minimum 4 and maximum 8 employees
- S shift should have minimum 3 and maximum 6 employees
- When filling shifts to meet target hours, the distribution should respect these ratios
- Currently, S shift was getting more assignments than F shift

### Root Cause
The solver used hardcoded understaffing penalty weights:
```python
# Old hardcoded weights
shift_priority_weights = {
    'F': 20,  # Früh/Early
    'S': 12,  # Spät/Late  
    'N': 5    # Nacht/Night
}
```

These didn't scale with actual database configuration, so if the max_staff values changed in the database, the priorities wouldn't adjust accordingly.

## Solution

### 1. Module-Level Constants

Added configurable constants to `solver.py`:

```python
UNDERSTAFFING_BASE_WEIGHT = 5  # Baseline minimum weight for any shift
UNDERSTAFFING_WEIGHT_MULTIPLIER = 2.5  # Ensures separation without exceeding team priority
SHIFT_PREFERENCE_BASE_WEIGHT = 15  # Must be < team priority (50) to avoid override
TEAM_PRIORITY_VIOLATION_WEIGHT = 50  # Must be higher than understaffing weights
```

### 2. Dynamic Understaffing Weight Calculation

Calculates weights proportional to `max_staff_weekday` from the database:

```python
# Formula
weight = UNDERSTAFFING_BASE_WEIGHT * (max_staff / min_max_staff) * UNDERSTAFFING_WEIGHT_MULTIPLIER

# Example with F(max=8), S(max=6), N(max=4)
min_max_staff = 4
F_weight = 5 * (8/4) * 2.5 = 25
S_weight = 5 * (6/4) * 2.5 = 19  
N_weight = 5 * (4/4) * 2.5 = 12

# Result: F gets highest priority, then S, then N
```

**Safety Feature**: Weights are capped at `TEAM_PRIORITY_VIOLATION_WEIGHT - 1` to ensure team cohesion always takes precedence.

### 3. Dynamic Shift Preference Weights

Calculates rewards/penalties inversely proportional to `max_staff`:

```python
# Formula  
weight = SHIFT_PREFERENCE_BASE_WEIGHT * (1 - 2 * max_staff / max_of_max_staff)

# Example with F(max=8), S(max=6), N(max=4)
max_of_max_staff = 8
F_weight = 15 * (1 - 2*8/8) = 15 * (1 - 2) = -15  (reward)
S_weight = 15 * (1 - 2*6/8) = 15 * (1 - 1.5) = -8  (smaller reward)
N_weight = 15 * (1 - 2*4/8) = 15 * (1 - 1) = 0     (neutral)

# Negative values = rewards (encouraged), positive = penalties (discouraged)
```

**Range**: Always bounded in [-15, +15] by formula design.

## Weight Hierarchy

The complete soft constraint hierarchy (from highest to lowest priority):

1. **TEAM_PRIORITY_VIOLATION_WEIGHT = 50**
   - Keeps teams together
   - Penalizes cross-team assignments when team has capacity
   - HIGHEST priority to maintain operational efficiency

2. **Understaffing Penalties: 12-49 (dynamic)**
   - Encourages filling shifts to capacity
   - Scaled based on shift capacity from database
   - Capped to stay below team priority

3. **Shift Preferences: ±15**
   - Rewards assigning employees to high-capacity shifts
   - Penalizes overusing low-capacity shifts
   - Complements understaffing penalties

4. **Other Soft Constraints**: < 50
   - Weekday/weekend overstaffing
   - Fairness objectives
   - Block scheduling bonuses

## Benefits

### 1. Database-Driven Configuration
Shift priorities automatically adjust when shift settings change in the database. No code changes needed.

### 2. Proportional Distribution
Shifts with higher capacity get proportionally more assignments, respecting operational requirements.

### 3. Maintains Team Cohesion
By capping weights below team priority (50), the system ensures teams stay together, which is operationally more important than perfect distribution ratios.

### 4. Transparency
Debug output shows calculated weights:
```
Calculated dynamic shift priority weights based on max_staff: {'F': 25, 'S': 19, 'N': 12}
Shift penalty/reward weights (negative=reward): {'F': -15, 'S': -8, 'N': 0}
```

## Testing

### Test 1: Team Priority (`test_team_priority.py`)
**Purpose**: Verify team cohesion is preserved  
**Result**: ✓ PASS - No cross-team violations

### Test 2: Shift Distribution (`test_shift_distribution_ratios.py`)
**Purpose**: Verify F > S > N ordering based on max_staff  
**Result**: ✓ PASS - Correct ordering achieved

### Code Quality
- Code Review: ✓ PASS (all comments addressed)
- CodeQL Security Scan: ✓ PASS (0 alerts)

## Configuration

To adjust the balance between shift distribution and other constraints, modify these constants in `solver.py`:

```python
# Increase to strengthen shift distribution priority
UNDERSTAFFING_WEIGHT_MULTIPLIER = 2.5  

# Increase to strengthen shift preference (but keep < 50)
SHIFT_PREFERENCE_BASE_WEIGHT = 15

# Increase to strengthen team cohesion (must be highest)
TEAM_PRIORITY_VIOLATION_WEIGHT = 50
```

**Important**: `TEAM_PRIORITY_VIOLATION_WEIGHT` must always be higher than any understaffing weight to maintain operational team cohesion.

## Expected Behavior

### Scenario: Monthly Planning
Given shift configuration:
- F: min 4, max 8 employees per day
- S: min 3, max 6 employees per day  
- N: min 3, max 4 employees per day

Expected outcome:
- ✅ F shift gets the most weekday assignments
- ✅ S shift gets medium number of assignments
- ✅ N shift gets the fewest assignments
- ✅ Teams stay together (no unnecessary cross-team assignments)
- ✅ All employees reach target hours (~192h/month)

### Tolerance
Distribution ratios may vary ±20% from theoretical ideal due to:
- Team rotation patterns (F → N → S)
- Rest time constraints (11h minimum)
- Shift grouping rules (avoid isolated shifts)
- Consecutive shift limits
- Individual absences

This is expected and acceptable - the important requirement is the **ordering** (F > S > N), not exact ratios.

## Migration Notes

### For Existing Deployments
No migration needed. The change is backward compatible:
- Uses existing `max_staff_weekday` field from `ShiftTypes` table
- Falls back to hardcoded weights if shift types are not available
- Does not change database schema

### For New Deployments
- Ensure `ShiftTypes` table has correct `max_staff_weekday` values
- Higher max_staff = higher priority for that shift type
- System will automatically calculate appropriate weights

## Troubleshooting

### Issue: S shift still gets more assignments than F
**Diagnosis**: Check if F and S have different `max_staff_weekday` values in database  
**Solution**: Update database settings to reflect operational requirements

### Issue: Too many cross-team assignments
**Diagnosis**: Shift distribution weights might be too high  
**Solution**: Decrease `UNDERSTAFFING_WEIGHT_MULTIPLIER` or `SHIFT_PREFERENCE_BASE_WEIGHT`

### Issue: Shifts not filling to capacity  
**Diagnosis**: Weights might be too low
**Solution**: Increase `UNDERSTAFFING_WEIGHT_MULTIPLIER` (but keep < 50/base)

## References

- Original issue report: Problem statement in PR description
- Implementation: `solver.py` lines 30-57, 360-380, 441-456
- Tests: `test_shift_distribution_ratios.py`, `test_team_priority.py`
