# Fix: April 2026 Planning Infeasibility - Conflicting Team Locks

## Problem Summary

When planning April 2026, users encountered an INFEASIBLE error with numerous warnings:

```
WARNING: Skipping conflicting locked shift for team 1, week 0
  Existing: F, Attempted: S (from employee 2 on 2026-03-30)
WARNING: Skipping conflicting locked shift for team 1, week 0
  Existing: F, Attempted: S (from employee 5 on 2026-03-31)
WARNING: Skipping conflicting locked shift for team 3, week 0
  Existing: F, Attempted: N (from employee 13 on 2026-03-30)
[... many similar warnings ...]

✗ INFEASIBLE - No solution exists!
```

### Dates Involved
- Week 0 spans: March 30 (Monday) - April 5 (Sunday)
- All warnings are for dates in this boundary week
- All existing locks show shift 'F' (Früh/Early)
- Attempted assignments are shifts 'S' (Spät/Late) and 'N' (Nacht/Night)

## Root Cause

The bug was in `web_api.py` lines 2753-2758:

```python
# Lock existing team assignments
for team_id, date_str, shift_code in existing_team_assignments:
    assignment_date = date.fromisoformat(date_str)
    if assignment_date in date_to_week:
        week_idx = date_to_week[assignment_date]
        locked_team_shift[(team_id, week_idx)] = shift_code  # BUG: Can overwrite!
        app.logger.info(f"Locked: Team {team_id}, Week {week_idx} -> {shift_code}")
```

### Why This Failed

1. **Database Query**: The code queries existing shift assignments from adjacent months (e.g., March 30-31 when planning April)
2. **Team-based Planning**: In this system, all team members work the same shift during a week
3. **Multiple Assignments**: If different employees from the same team worked different shifts on different days within the same week, the database returns multiple records
4. **Overwriting Bug**: The code would overwrite `locked_team_shift[(team_id, week_idx)]` multiple times with different shift codes
5. **Conflict**: Later, `model.py` processes `locked_employee_shift` and tries to add more locks, creating conflicts
6. **Result**: The solver becomes INFEASIBLE because the model has contradictory constraints

### Example Scenario

Database contains:
- Employee 2 (Team 1) worked shift 'F' on March 30 (week 0)
- Employee 5 (Team 1) worked shift 'S' on March 31 (week 0)
- Employee 6 (Team 1) worked shift 'N' on April 1 (week 0)

The old code would:
1. Set `locked_team_shift[(1, 0)] = 'F'` (from first record)
2. Overwrite to `locked_team_shift[(1, 0)] = 'S'` (from second record)
3. Overwrite to `locked_team_shift[(1, 0)] = 'N'` (from third record)
4. End result: Team 1, week 0 is locked to 'N' (the last one processed)

Then when `model.py` processes employee locks, it tries to lock Team 1 to 'F' or 'S' based on employee data, creating conflicts and INFEASIBLE.

## Solution

Modified `web_api.py` lines 2752-2783 to use a two-pass conflict detection algorithm:

```python
# Lock existing team assignments
# CRITICAL FIX: Detect and handle conflicting team assignments within the same week
# If multiple assignments exist for the same team in the same week with different shifts,
# we should NOT lock the team to any shift (let the solver decide) to avoid INFEASIBLE errors

# First pass: identify conflicts
conflicting_team_weeks = set()  # Track (team_id, week_idx) pairs with conflicts
for team_id, date_str, shift_code in existing_team_assignments:
    assignment_date = date.fromisoformat(date_str)
    if assignment_date in date_to_week:
        week_idx = date_to_week[assignment_date]
        
        # Check for conflicts
        if (team_id, week_idx) in locked_team_shift:
            existing_shift = locked_team_shift[(team_id, week_idx)]
            if existing_shift != shift_code:
                # Conflict detected: different shift codes for same team/week
                app.logger.warning(f"CONFLICT: Team {team_id}, Week {week_idx} has conflicting shifts: {existing_shift} vs {shift_code}")
                conflicting_team_weeks.add((team_id, week_idx))
        else:
            # No conflict yet - tentatively add this lock
            locked_team_shift[(team_id, week_idx)] = shift_code

# Second pass: remove all conflicting locks
for team_id, week_idx in conflicting_team_weeks:
    if (team_id, week_idx) in locked_team_shift:
        app.logger.warning(f"  Removing team lock for Team {team_id}, Week {week_idx} to avoid INFEASIBLE")
        del locked_team_shift[(team_id, week_idx)]

# Log remaining locks
for (team_id, week_idx), shift_code in locked_team_shift.items():
    app.logger.info(f"Locked: Team {team_id}, Week {week_idx} -> {shift_code} (from existing assignments)")
```

### How It Works

1. **First Pass**: 
   - Iterate through all assignments
   - Tentatively add locks to `locked_team_shift`
   - Track any (team_id, week_idx) pairs that have conflicts in `conflicting_team_weeks`

2. **Second Pass**:
   - Remove all locks for (team_id, week_idx) pairs that had conflicts
   - Log warnings for each removed lock

3. **Result**:
   - Teams with consistent shift assignments across a week: Locked (preserves existing behavior)
   - Teams with conflicting shift assignments: NOT locked (allows solver to find solution)
   - No INFEASIBLE errors due to contradictory constraints

## Files Changed

### Backend
- `web_api.py`: Added two-pass conflict detection logic (lines 2752-2783)

### Tests
- `test_web_api_conflict_detection.py`: NEW - Unit test for conflict detection logic
- `test_april_2026_conflict_fix.py`: NEW - Integration test reproducing user scenario
- Updated test documentation to clarify testing approach

## Testing

### New Tests
✓ `test_web_api_conflict_detection.py` - Directly tests the conflict detection logic with simulated database records
✓ `test_april_2026_conflict_fix.py` - Tests that the model can handle April 2026 planning with conflicting locks

### Existing Tests
✓ `test_april_2026_boundary_fix.py` - Verifies April boundary week handling still works
✓ `test_boundary_week_fix.py` - Verifies general boundary week handling still works

### Security Review
✓ CodeQL analysis: 0 alerts found (Python)

## Impact

### User-Visible Changes
1. **April 2026 (and similar months) can now be planned successfully** even when there are conflicting shift assignments from previous months
2. **Warning messages** logged when conflicts are detected (for debugging)
3. **No breaking changes** to existing functionality

### Technical Benefits
1. **Robust conflict handling**: System can handle inconsistent database data
2. **Preserves optimization**: Teams with consistent shifts are still locked (reduces search space)
3. **Graceful degradation**: Teams with conflicts simply aren't locked (solver finds solution)
4. **Better logging**: Clear warnings when conflicts are detected for debugging

## Why This Fix Is Minimal

The fix is surgical and targeted:
- Only modified the lock-building logic in `web_api.py`
- Added conflict detection without changing the overall architecture
- Preserves existing behavior for non-conflicting cases
- No changes to database schema or API contracts
- All existing tests continue to pass

## Future Considerations

This fix addresses the symptom (conflicting locks) rather than the root cause (why different employees from the same team have different shifts in the database). However:

1. **This is the correct approach** because:
   - The database may legitimately have such data when planning across month boundaries
   - Different employees may have worked on different days in the previous month
   - The team-based model is designed for weekly planning, not daily planning

2. **No further action needed** unless:
   - Users report that the solver is taking too long without team locks
   - Data quality issues are identified in the database
   - Business rules change to require stricter consistency

## Related Issues

This fix complements previous fixes for month-to-month planning:
- **BOUNDARY_WEEK_FIX.md**: Handled boundary week employee locks
- **FEBRUARY_2026_CONFLICT_FIX.md**: Handled team-level lock conflicts in model.py
- **Current fix**: Handles conflicts when loading from database in web_api.py

Together, these fixes ensure robust month-to-month planning without INFEASIBLE errors.
