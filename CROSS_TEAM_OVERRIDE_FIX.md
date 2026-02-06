# Cross-Team Override Fix - February 2026 Rotation Bug

## Problem Description

In the February 2026 shift schedule, employees were being assigned to shifts that violated their team's rotation pattern. Specifically:

**Issue:** Team Alpha members (like Anna Schmidt, PN002) were assigned S (Spätschicht/Late Shift) during ISO Week 9 (February 23-March 1, 2026), when the team's rotation pattern dictated they should work F (Frühschicht/Early Shift).

**Impact:**
- Employees worked 6+ consecutive days with the same shift type
- Team-based rotation pattern F→N→S was broken
- Individual team members had different shifts on the same weekdays
- Example: On Feb 23, most Team Alpha members had F, but Anna Schmidt had S

## Root Cause

The constraint system allowed employees to **bypass their team's assigned shift** and work different shift types through cross-team assignments on weekdays.

### How It Happened

1. **Team Rotation Constraint** (WORKING CORRECTLY):
   - Team Alpha was correctly assigned F for ISO Week 9
   - Constraint: `team_shift[Team Alpha, Week 9, "F"] = 1`

2. **Cross-Team Assignment Variables** (BUG):
   - Employees could set `employee_cross_team_shift[emp, date, "S"] = 1`
   - AND simultaneously set `employee_active[emp, date] = 0`
   - This meant: "Employee is NOT working with their team, but IS working shift S via cross-team"

3. **Missing Constraint**:
   - No constraint prevented employees from working a different shift type via cross-team when their team had a specific shift assigned
   - Result: Employees could "skip" their team's F shifts and work S shifts via cross-team assignments

## Solution

Added a **HARD CONSTRAINT** in `constraints.py` at lines 627-658 that enforces:

**Rule:** If a team works shift type X during week N, then team members CANNOT work any other shift type (Y, Z) via cross-team assignments on weekdays during week N.

### Implementation

```python
# FIX FOR BUG: Enforce that cross-team work cannot override team rotation on weekdays
for shift_code in shift_codes:
    # If team has this shift type this week
    if (team.id, week_idx, shift_code) in team_shift:
        # For each OTHER shift type
        for other_shift_code in shift_codes:
            if other_shift_code == shift_code:
                continue  # Same shift is OK
            
            # Collect all cross-team weekday variables
            cross_team_weekday_vars = []
            for d in week_dates:
                if d.weekday() < 5:  # Weekday only
                    if (emp.id, d, other_shift_code) in employee_cross_team_shift:
                        cross_team_weekday_vars.append(
                            employee_cross_team_shift[(emp.id, d, other_shift_code)]
                        )
            
            if cross_team_weekday_vars:
                # When team_shift[team, week, shift_code] = 1,
                # force all cross_team[emp, weekday, other_shift_code] = 0
                for cross_var in cross_team_weekday_vars:
                    model.Add(cross_var == 0).OnlyEnforceIf(
                        team_shift[(team.id, week_idx, shift_code)]
                    )
```

### Key Points

1. **Conditional Enforcement**: Uses `OnlyEnforceIf` to only apply when team has a specific shift
2. **Weekday Only**: Constraint only applies to Mon-Fri (weekends remain flexible)
3. **Preserves Cross-Team**: Still allows cross-team assignments for the SAME shift type as the team
4. **Team-Based Model**: Enforces the core principle that team members work together

## Testing

### New Test
Created `test_cross_team_fix.py` to verify:
- Team Alpha gets F for ISO Week 9 (Feb 23-Mar 1)
- Anna Schmidt and other Team Alpha members work F (not S) during that week
- Result: **PASS** ✅

### Existing Tests
All existing tests continue to pass:
- `test_rotation_order.py` - Rotation transitions ✅
- `test_database_rotation.py` - Database-driven rotation ✅
- `test_daily_shift_ratio.py` - F >= S constraint ✅
- `test_boundary_week_fix.py` - Month boundary handling ✅

### Security
- CodeQL scan: No vulnerabilities detected ✅

## Impact

### Before Fix
```
Team Alpha - ISO Week 9 (Feb 23-27):
- Robert Franke: F, F, F, F, F ← Following team
- Lisa Meyer:    F, F, F, F, F ← Following team
- Max Müller:    F, F, F, F, F ← Following team
- Peter Weber:   F, F, F, F, F ← Following team
- Anna Schmidt:  S, S, S, S, S ← BUG! Different shift
```

### After Fix
```
Team Alpha - ISO Week 9 (Feb 23-27):
- Robert Franke: F, F, F, F, F ← Following team
- Lisa Meyer:    F, F, F, F, F ← Following team
- Max Müller:    F, F, F, F, F ← Following team
- Peter Weber:   F, F, F, F, F ← Following team
- Anna Schmidt:  F, F, F, F, F ← FIXED! Same shift
```

## Related Documentation

This fix is similar to the previous "INTRA_WEEK_SHIFT_FIX" (documented in `INTRA_WEEK_SHIFT_FIX.md`), which prevented employees from switching shift types mid-week. This new fix prevents employees from bypassing their team's rotation entirely through cross-team assignments.

## Date
2026-02-06

## Author
Copilot (with Tim Ux)
