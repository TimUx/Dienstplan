# Fix for February 2026 Scheduling Infeasibility

## Problem Statement

After PR124 (which introduced ISO week-based rotation to fix month transition issues), scheduling for February 2026 fails with an INFEASIBLE constraint error, while January 2026 works fine.

**Error Message:**
```
INFEASIBLE: 'proven during initial copy of constraint #188:
linear {
  vars: [15, 16, 17]
  coeffs: [1, 1, 1]
  domain: [1, 1]
}
With current variable domains:
var:15 domain:[1]
var:16 domain:[1]
var:17 domain:[0,1]
```

This shows three variables that must sum to 1, but two are already fixed to 1, making it impossible (1+1+var17 ≠ 1).

## Root Cause Analysis

The issue occurs in the interaction between three constraint types:

1. **Team Shift Assignment** (`add_team_shift_assignment_constraints`): Enforces `sum(all shifts) == 1` for each team per week
2. **Team Rotation** (`add_team_rotation_constraints`): Forces specific shifts based on ISO week number calculation
3. **Locked Employee Shifts** (`_apply_locked_assignments`): Forces team shifts based on existing employee assignments

### The Conflict

When planning February 2026 with locked employee assignments from January:

1. `locked_employee_shift` contains assignments from previous planning periods
2. In `_apply_locked_assignments()` (line 214), these force team shifts via:
   ```python
   self.model.Add(self.team_shift[(emp.team_id, week_idx, shift_code)] == 1)
   ```
3. **BUT** this doesn't update `self.locked_team_shift`
4. Later, `add_team_rotation_constraints()` calculates which shift the team should have based on ISO week number
5. If the ISO week calculation produces a DIFFERENT shift, it also adds:
   ```python
   model.Add(team_shift[(team.id, week_idx, different_shift)] == 1)
   ```
6. Combined with the "exactly one shift per team" constraint, this creates:
   - `team_shift[(team, week, "F")] == 1` (from locked employee)
   - `team_shift[(team, week, "N")] == 1` (from rotation)
   - `sum(team_shift[(team, week, *)]) == 1` (from assignment constraint)
   - **INFEASIBLE!**

## Solution

The fix is simple but critical: when `_apply_locked_assignments()` forces a team shift from a locked employee assignment, it must also update `self.locked_team_shift`. This way, the rotation constraint will see the lock and skip that week (as designed on line 176-178 of `constraints.py`).

### Code Change

In `model.py`, `_apply_locked_assignments()` method (around line 215):

```python
# Lock the team to this shift for this week
if week_idx is not None and (emp.team_id, week_idx, shift_code) in self.team_shift:
    self.model.Add(self.team_shift[(emp.team_id, week_idx, shift_code)] == 1)
    # CRITICAL FIX: Update locked_team_shift so rotation constraint skips this week,
    # preventing conflicts between locked employee shifts and ISO week-based rotation
    if (emp.team_id, week_idx) not in self.locked_team_shift:
        self.locked_team_shift[(emp.team_id, week_idx)] = shift_code
```

The added lines ensure that when we force a team shift constraint, we also record it in `locked_team_shift` so the rotation constraint knows to skip it.

## Testing

### Unit Test
`test_locked_team_shift_update.py` - Verifies that `locked_team_shift` is properly updated when `locked_employee_shift` is applied.

**Result:** ✓ PASSED

### Integration Test  
`test_february_locked_constraints.py` - Simulates real-world scenario with locked constraints from January extending into February.

**Result:** ✓ PASSED - February 2026 planning succeeds with 3 locked constraints

### Regression Test
`test_month_transition_fix.py` - Existing test for month transition handling (the original PR124 fix).

**Result:** ✓ PASSED - No regression, month transitions still work correctly

### Final Verification
`test_january_february_2026.py` - Direct test of the problem statement scenario.

**Results:**
- January 2026: ✓ SUCCESS
- February 2026: ✓ SUCCESS

## Impact

### Fixed
- ✅ February 2026 planning now works
- ✅ Any month planning with locked constraints from previous periods works
- ✅ Cross-month planning continues to function correctly

### No Regression
- ✅ Month transition handling still works (ISO week-based rotation)
- ✅ All existing tests pass
- ✅ No security vulnerabilities introduced

## Files Modified

1. **model.py** - Added 2 lines to `_apply_locked_assignments()` to update `locked_team_shift`
2. **test_locked_team_shift_update.py** (new) - Unit test
3. **test_february_locked_constraints.py** (new) - Integration test
4. **test_january_february_2026.py** (new) - Final verification

## Conclusion

This was a subtle but critical bug where two separate parts of the system (locked employee assignments and rotation constraints) didn't properly communicate their intent. The fix ensures they work in harmony by updating the shared `locked_team_shift` dictionary that the rotation constraint checks before forcing shifts.

The root cause was introduced when PR124 added ISO week-based rotation to fix month transitions, but didn't account for how locked employee assignments interact with the rotation system. This fix completes the cross-month planning feature.
