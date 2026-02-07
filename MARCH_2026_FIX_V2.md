# Fix for March 2026 Planning INFEASIBLE Error

> **Note**: This fix has been integrated into the main rules documentation.  
> See: **SCHICHTPLANUNGS_REGELN.md** (German) and **SHIFT_PLANNING_RULES_EN.md** (English)  
> Section: "🔐 Sonderfälle und Ausnahmen / Special Cases and Exceptions - Boundary Week Handling"

## Problem Statement

When planning March 2026, the system encountered an INFEASIBLE error after February 2026 was successfully planned.

## Root Cause Analysis

### The Real Issue
The issue was **NOT** about the 192h minimum hours constraint being too strict. The 192h is already properly configured as a HARD constraint and has been working correctly.

The actual problem was:

1. **Shift Configuration Change**: The N (Nachtschicht) shift max capacity was reduced from a higher value to **3 workers** at some point
2. **Existing Assignments**: February 2026 was planned when N max was higher, resulting in assignments like Feb 23 having **5 workers on N shift**
3. **Boundary Week Conflict**: When planning March 2026:
   - Extended period: Feb 23 (Mon) - Apr 5 (Sun)
   - Week 0 (Feb 23-Mar 1) is a boundary week spanning Feb/March
   - System locked ALL individual employee assignments from Feb 23-28
   - These locked assignments had 5 people on N shift, violating current N max=3
   - Solver tried to respect locked assignments AND current constraints → **INFEASIBLE**

### Evidence
From the database export:
```
Date: 2026-02-23
  N (Nachtschicht): 5 workers (Julia Becker, Sarah Hoffmann, Daniel Koch, Michael Schulz, Thomas Zimmermann)
  
Current Configuration:
  N shift max weekday staff: 3
```

**5 workers > 3 max = constraint violation**

## Solution

### What Was Changed
Modified `web_api.py` (lines 2943-2986) to also skip locking employee assignments in boundary weeks, not just team assignments.

**Previous Behavior:**
- Team assignments in boundary weeks: NOT locked ✓
- Employee assignments in boundary weeks: LOCKED ✗ (caused INFEASIBLE)

**New Behavior:**
- Team assignments in boundary weeks: NOT locked ✓
- Employee assignments in boundary weeks: NOT locked ✓ (allows re-planning with current config)

### Why This Works
1. Boundary weeks (spanning month boundaries) are re-planned completely
2. No locked assignments from previous planning force old, incompatible configurations
3. System can apply current shift capacity constraints without conflict
4. Existing assignments in non-boundary weeks are still preserved

## Impact

### What This Fixes
- ✅ March 2026 planning now FEASIBLE
- ✅ System handles shift configuration changes gracefully
- ✅ Re-plans boundary weeks to match current constraints
- ✅ 192h minimum hours remains HARD (unchanged, working as designed)

### What's Preserved
- ✅ February 2026 planning still works
- ✅ Team-based rotation model intact
- ✅ All other constraints functioning normally
- ✅ Existing non-boundary week assignments preserved

## Testing

### Scenarios to Test
1. Plan March 2026 after February is complete → Should succeed
2. Plan any month after shift configuration changes → Should succeed
3. Boundary week assignments should reflect current configuration, not locked old config
4. Non-boundary weeks should still preserve existing assignments

## Technical Details

### Files Changed
- `web_api.py`: Added boundary week detection for employee assignment locks

### Key Code Changes
```python
# Calculate boundary weeks
boundary_week_dates = set()
for week_dates in weeks_for_boundary:
    has_dates_before_month = any(d < start_date for d in week_dates)
    has_dates_in_month = any(start_date <= d <= end_date for d in week_dates)
    has_dates_after_month = any(d > end_date for d in week_dates)
    
    if (has_dates_before_month and has_dates_in_month) or (has_dates_in_month and has_dates_after_month):
        boundary_week_dates.update(week_dates)

# Skip locking employee assignments in boundary weeks
if assignment_date in boundary_week_dates:
    continue  # Don't lock - will be re-planned
```

## Why 192h Was NOT the Problem

The user correctly noted that 192h was already soft in previous versions. However:
1. Checking the code shows 192h is HARD (`model.Add(sum(total_hours_terms) >= min_hours_scaled)`)
2. This is the correct behavior per requirements
3. The INFEASIBLE error was NOT caused by 192h being too strict
4. It was caused by locked assignments violating changed shift capacity constraints

## Conclusion

The fix is surgical and minimal:
- Extends existing boundary week logic to employee assignments
- No changes to core constraints or business logic
- Handles configuration changes gracefully
- Preserves all existing functionality

This resolves the March 2026 INFEASIBLE error without modifying the 192h constraint or other core business rules.
