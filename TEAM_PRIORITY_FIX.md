# Team Priority Fix - Shift Assignment

## Problem Statement

When filling shifts to meet staffing requirements, the system was incorrectly using cross-team members before exhausting own team members. This violated the principle that **team shifts should primarily be filled with their own team members**, and only when all team members are in the same shift should cross-team members be used.

### Example

From the user's problem statement, in Week 2:
- **Sarah Hoffmann (PN008)** from Team Beta was assigned **F shift**, even though her team had **S shift**
- **Markus Richter (PN011)** from Team Gamma was assigned **S shift**, even though his team had **F shift**

The correct assignment should have been:
- Sarah Hoffmann (Team Beta) → **S shift** (her team's shift)
- Markus Richter (Team Gamma) → **F shift** (his team's shift)

## Root Cause

The constraint solver uses penalty weights to prioritize different objectives. The issue was that the **team priority violation weight** (10) was **lower** than the **weekday understaffing penalties**:

| Constraint | Weight | Priority |
|------------|--------|----------|
| Weekday understaffing (F) | 20 | Higher |
| Weekday understaffing (S) | 12 | Higher |
| **Team priority violations** | **10** | **Lower** ❌ |
| Weekday understaffing (N) | 5 | Lower |

This caused the solver to prefer filling shifts with cross-team workers (to avoid understaffing penalties of 20/12) rather than keeping teams together (penalty of only 10).

## Solution

**Increased the team priority violation weight from 10 to 50** in `solver.py`.

This ensures that team cohesion takes priority over shift filling optimization:

| Constraint | Old Weight | New Weight | Result |
|------------|-----------|------------|--------|
| **Team priority violations** | 10 | **50** | ✅ **Highest priority** |
| Weekday understaffing (F) | 20 | 20 | Lower priority |
| Weekday understaffing (S) | 12 | 12 | Lower priority |
| Weekday understaffing (N) | 5 | 5 | Lower priority |

### Code Change

**File**: `solver.py` (lines 372-378)

```python
# OLD (weight 10):
if team_priority_violations:
    print(f"  Adding {len(team_priority_violations)} team priority violation penalties (weight 10x)...")
    for violation_var in team_priority_violations:
        objective_terms.append(violation_var * 10)

# NEW (weight 50):
if team_priority_violations:
    print(f"  Adding {len(team_priority_violations)} team priority violation penalties (weight 50x)...")
    for violation_var in team_priority_violations:
        objective_terms.append(violation_var * 50)
```

## How It Works

The team priority violation penalty is calculated in `constraints.py` (lines 866-883):

1. For each shift on each day, the system counts:
   - **team_count**: Number of team members working (from the team assigned to that shift)
   - **cross_team_count**: Number of cross-team workers helping
   - **unfilled_capacity**: How many more team members could work (max_staff - team_count)

2. **Violation = min(unfilled_capacity, cross_team_count)**
   - This represents how many cross-team workers are being used when team members are available

3. With the new weight of 50:
   - Using 1 cross-team worker when 1 team member is available = **50 penalty**
   - This is now more expensive than understaffing F shift by 2 workers (20 × 2 = 40)
   - Therefore, the solver will prioritize team members first

## Verification

### New Test Case

Created `test_team_priority.py` that specifically tests this scenario:
- Sets up 2 teams (Beta and Gamma) with 5 members each
- Locks Beta to S shift and Gamma to F shift for a specific week
- Verifies no cross-team violations occur
- **Result**: ✅ PASS

### Existing Tests

All existing tests continue to pass:
- ✅ `test_real_scenario.py`
- ✅ `test_rotation_order.py`
- ✅ `test_boundary_week_fix.py`
- ✅ `test_partial_week_absence.py`

## Impact

### Positive Effects

1. **Teams stay together**: Team members are assigned to their team's scheduled shifts
2. **Better work coordination**: Teams work the same shifts, improving collaboration
3. **Predictable schedules**: Employees know which shift they'll work based on their team's rotation

### No Negative Effects

- The change only affects the **priority** of assignments, not feasibility
- Cross-team assignments are still **allowed** when necessary (e.g., when a team has insufficient members)
- All other constraints remain unchanged
- No performance impact (same complexity)

## Technical Details

### Constraint Priority Hierarchy

After this fix, the priority hierarchy is:

1. **Hours shortage (100)**: Employees MUST reach 192h monthly target
2. **Team priority (50)**: Teams MUST be kept together when possible
3. **Weekend overstaffing (50)**: Strongly discourage weekend overstaffing
4. **Weekday understaffing (20/12/5)**: Encourage filling weekdays to capacity
5. **Weekday overstaffing (1)**: Allow weekday overstaffing if needed

### When Cross-Team Assignments Still Occur

Cross-team assignments are still used (and appropriate) when:
- Team has insufficient members to meet minimum staffing
- Team members are absent
- Employees need additional hours to reach 192h minimum
- All team members are already working maximum hours

## Conclusion

This fix ensures that the shift planning system respects team cohesion as a top priority while still maintaining flexibility for necessary cross-team assignments. The principle of "fill team shifts with team members first, then use cross-team workers" is now properly enforced.
