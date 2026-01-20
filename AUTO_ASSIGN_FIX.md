# Fix for INFEASIBLE Issue - TeamShiftAssignments Auto-Assignment

## Problem
When teams have empty `allowed_shift_type_ids` (no TeamShiftAssignments configured in database), the shift planner could become INFEASIBLE because:

1. Empty `allowed_shift_type_ids` → Teams can work all shifts (backward compatibility)
2. But if database is inconsistent or misconfigured:
   - No teams are allowed to work F, S, N shifts
   - Staffing still requires F, S, N coverage
   - Result: INFEASIBLE

## Root Cause
The `data_loader.py` assigned empty list to teams without TeamShiftAssignments:
```python
team.allowed_shift_type_ids = team_shift_assignments.get(team.id, [])
```

Empty list is treated as "can work all shifts" in constraint logic, BUT:
- If database has NO TeamShiftAssignments at all → works fine
- If database has TeamShiftAssignments for SOME teams but not others → mixed behavior
- If someone accidentally configured teams with wrong shifts → INFEASIBLE

## Solution
Auto-assign F, S, N shifts to teams with empty `allowed_shift_type_ids`:

```python
# Auto-assign F, S, N to teams with empty configuration (backward compatibility)
if not team.allowed_shift_type_ids and not team.is_virtual:
    # Find F, S, N shift type IDs from loaded shift types
    f_id = next((st.id for st in shift_types if st.code == "F"), None)
    s_id = next((st.id for st in shift_types if st.code == "S"), None)
    n_id = next((st.id for st in shift_types if st.code == "N"), None)
    
    # Only assign if all three shifts exist
    if f_id and s_id and n_id:
        team.allowed_shift_type_ids = [f_id, s_id, n_id]
        print(f"  Auto-assigned F, S, N shifts to {team.name} (no TeamShiftAssignments found)")
```

## Benefits
1. **Prevents INFEASIBLE**: Teams always have at least F, S, N if no other configuration exists
2. **Backward compatible**: Existing systems without TeamShiftAssignments continue to work
3. **Clear behavior**: Explicit log message shows when auto-assignment happens
4. **Safe**: Only applies to non-virtual teams, only when F,S,N exist

## Testing
- ✅ `test_infeasible_issue.py`: Empty allowed_shift_type_ids → OPTIMAL (auto-assigned)
- ✅ `test_infeasible_with_allowed_shifts.py`: Explicit [F,S,N] → OPTIMAL (unchanged)
- ✅ `test_infeasible_wrong_shifts.py`: Wrong shifts [ZD,BMT,BSB] → INFEASIBLE (as expected)

## Migration
No database changes required. The fix is transparent and happens at runtime during data loading.

## User Communication
When the fix triggers, users will see:
```
Loading data from database...
  Auto-assigned F, S, N shifts to Team 1 (no TeamShiftAssignments found)
  Auto-assigned F, S, N shifts to Team 2 (no TeamShiftAssignments found)
```

This helps users understand that their database needs TeamShiftAssignments configuration.

## Future Enhancements
Consider adding validation to detect and warn about:
- Teams with shift assignments that don't include F, N, S (can't participate in rotation)
- Inconsistent configurations between teams
- Missing shift types in database
