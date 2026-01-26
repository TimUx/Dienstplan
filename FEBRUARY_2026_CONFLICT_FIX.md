# Februar 2026 Scheduling Fix - Locked Team Shift Conflicts

## Problem

When planning February 2026 after successfully planning January 2026, the CP-SAT solver reported INFEASIBLE:

```
INFEASIBLE: 'proven during initial copy of constraint #181:
linear {
  vars: [0, 1, 2]
  coeffs: [1, 1, 1]
  domain: [1, 1]
}
With current variable domains:
var:0 domain:[0,1]
var:1 domain:[1]
var:2 domain:[1]
```

This error indicates that:
- Constraint #181 requires the sum of three variables to equal 1
- But var:1 and var:2 are both forced to 1
- Therefore sum ≥ 2, making it impossible to satisfy the constraint

## Root Cause

The issue was in `model.py`, in the `_apply_locked_assignments()` method (lines 213-218):

```python
# OLD CODE (BUGGY):
if week_idx is not None and (emp.team_id, week_idx, shift_code) in self.team_shift:
    self.model.Add(self.team_shift[(emp.team_id, week_idx, shift_code)] == 1)
    # CRITICAL FIX: Update locked_team_shift so rotation constraint skips this week,
    # preventing conflicts between locked employee shifts and ISO week-based rotation
    if (emp.team_id, week_idx) not in self.locked_team_shift:
        self.locked_team_shift[(emp.team_id, week_idx)] = shift_code
```

### The Race Condition

1. When planning February 2026, the system loads locked employee shifts from January that extend into February's first week
2. For each locked employee shift, it adds a constraint: `team_shift[(team_id, week_idx, shift_code)] == 1`
3. It then updates the `locked_team_shift` dictionary AFTER adding the constraint
4. If multiple employees from the **same team** have different locked shifts for the **same week**, both constraints get added:
   - Employee 1 (Team 1): `team_shift[(1, 0, "F")] == 1`
   - Employee 2 (Team 1): `team_shift[(1, 0, "N")] == 1`
5. The "exactly one shift per team per week" constraint requires: `sum(all shifts) == 1`
6. This creates an impossible situation: F + N + ... = 1, but both F and N must be 1

### Why This Happens at Month Boundaries

Month boundaries are particularly problematic because:
- January planning extends to complete weeks (Mon-Sun)
- If January ends on a Friday, the planning includes the full week (Mon Jan 27 - Sun Feb 2)
- February planning also includes this overlapping week
- The overlapping week creates locked employee shifts that can conflict if team members worked different shifts on different days of the same week

## Solution

Modified `_apply_locked_assignments()` to check for conflicts BEFORE adding constraints:

```python
# NEW CODE (FIXED):
if week_idx is not None and (emp.team_id, week_idx, shift_code) in self.team_shift:
    # CRITICAL FIX: Check for conflicts BEFORE adding constraint
    # Update locked_team_shift BEFORE adding the constraint to prevent race conditions
    if (emp.team_id, week_idx) in self.locked_team_shift:
        existing_shift = self.locked_team_shift[(emp.team_id, week_idx)]
        if existing_shift != shift_code:
            # Conflict detected: different locked shifts for same team/week
            # This can happen when multiple employees from the same team have
            # different locked shifts for overlapping weeks across month boundaries
            print(f"WARNING: Skipping conflicting locked shift for team {emp.team_id}, week {week_idx}")
            print(f"  Existing: {existing_shift}, Attempted: {shift_code} (from employee {emp_id} on {d})")
            continue  # Skip this lock to avoid infeasibility
    else:
        # No conflict - safe to lock this team/week to this shift
        self.locked_team_shift[(emp.team_id, week_idx)] = shift_code
    
    # Add the constraint only if we didn't skip due to conflict
    if self.locked_team_shift.get((emp.team_id, week_idx)) == shift_code:
        self.model.Add(self.team_shift[(emp.team_id, week_idx, shift_code)] == 1)
```

### Key Improvements

1. **Check before adding**: Verifies if a lock already exists before adding a constraint
2. **Update dictionary first**: Updates `locked_team_shift` BEFORE adding the constraint, not after
3. **Conflict detection**: Detects when two different shifts are being locked for the same team/week
4. **Graceful handling**: Skips conflicting locks with a warning instead of creating infeasible constraints

## Testing

Created comprehensive test `test_february_2026_conflict_fix.py` with two test scenarios:

### Test 1: Conflicting Locked Shifts
- Creates a scenario where two employees from the same team have different locked shifts in the same week
- Verifies the system handles the conflict gracefully without INFEASIBLE errors

### Test 2: Full January → February Scenario
- Plans January 2026
- Extracts locked shifts from January that extend into February
- Plans February 2026 with those locked shifts
- Verifies both months plan successfully

### Test Results

All tests pass:
```
✓ Conflict handling test: PASSED
✓ Full scenario test: PASSED
✓ Existing January-February 2026 test: PASSED
✓ Existing locked constraints test: PASSED
```

## Impact

This fix ensures that:
1. February 2026 (and all future months) can be planned successfully after planning previous months
2. Locked employee shifts from previous months are respected where possible
3. Conflicting locks are handled gracefully with warnings instead of causing INFEASIBLE errors
4. The team-based rotation pattern remains consistent across month boundaries

## Related Issues

This fix builds upon the work done in PR #126, which addressed ISO week-based rotation consistency across month boundaries. The combination of both fixes ensures robust month-to-month planning.
