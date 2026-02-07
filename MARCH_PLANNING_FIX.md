# Fix for March 2026 Planning Conflict

> **Note**: This fix has been integrated into the main rules documentation.  
> See: **SCHICHTPLANUNGS_REGELN.md** (German) and **SHIFT_PLANNING_RULES_EN.md** (English)  
> Section: "🔐 Sonderfälle und Ausnahmen / Special Cases and Exceptions - Boundary Week Handling"

## Problem Statement

When planning shifts for March 2026, the system encountered an INFEASIBLE error with conflicting team shift assignments in Week 0:

```
WARNING:web_api:CONFLICT: Team 1, Week 0 has conflicting shifts: F vs S
WARNING:web_api:CONFLICT: Team 2, Week 0 has conflicting shifts: N vs F
```

## Root Cause Analysis

### Timeline
- **February 2026** was successfully planned (Feb 1-28)
- **March 2026** planning failed (Mar 1-31)

### Technical Details
1. March 1, 2026 is a **Sunday**, so the extended planning period extends back to complete weeks
2. Extended planning period: **Feb 23 (Monday) to Apr 5 (Sunday)**
3. **Week 0** includes: Feb 23-28 (Monday-Saturday) + Mar 1 (Sunday)

### The Conflict
- Week 0 spans the boundary between February (already planned) and March (being planned)
- The system tried to lock Team 1 and Team 2 to specific shifts for the entire Week 0
- However, during Feb 23-28 (already planned as part of February), different employees from the same team worked different shifts on different days
- When the system tried to enforce a single shift for the team for the entire week, it created conflicts:
  - Team 1: Some assignments show "F" (Früh/Early), others show "S" (Spät/Late)
  - Team 2: Some assignments show "N" (Nacht/Night), others show "F" (Früh/Early)

## Solution

Modified `web_api.py` to identify and skip locking team shifts for weeks that span month boundaries.

### Implementation

1. **Identify boundary weeks**: Before attempting to lock team shifts, identify all weeks that contain dates both inside AND outside the main planning month
2. **Skip boundary weeks**: Do not attempt to lock team shifts for weeks that span boundaries
3. **Preserve existing logic**: Keep the conflict detection for non-boundary weeks

### Code Changes

**File**: `web_api.py` (lines 2838-2894)

Added logic to:
1. Iterate through all weeks in the extended planning period
2. Check if each week contains dates from both adjacent month(s) and current month
3. Mark such weeks as "boundary weeks"
4. Skip team shift locking for boundary weeks

### Example for March 2026

- **Week 0** (Feb 23 - Mar 1): Spans boundary → **NOT locked**
- **Weeks 1-4** (entirely in March): Current month → **NOT locked** (will be planned)
- **Week 5** (Mar 30 - Apr 5): Spans boundary → **NOT locked**

## Testing

Created `test_boundary_week_fix.py` to verify:
- ✅ Week 0 (Feb 23 - Mar 1) is correctly identified as a boundary week
- ✅ Week 5 (Mar 30 - Apr 5) is correctly identified as a boundary week
- ✅ Weeks 1-4 (entirely within March) are NOT boundary weeks
- ✅ February 2026 scenario still works correctly

## Impact

- **March 2026 planning**: Should now succeed without INFEASIBLE errors
- **February 2026 planning**: Unchanged, should continue to work
- **Other months**: Will benefit from the same fix when they have boundary weeks

## Security

- ✅ CodeQL security scan passed with 0 alerts
- ✅ No security vulnerabilities introduced

## Files Changed

1. `web_api.py` - Added boundary week detection and skipping logic
2. `test_boundary_week_fix.py` - New test file to verify the fix
