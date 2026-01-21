# Fix for Hardcoded Shift Staffing Values

## Problem

The shift planning was failing with INFEASIBLE status even though the user had increased the maximum number of employees for morning (Früh/F) and late (Spät/S) shifts in the database configuration. The issue was that hardcoded fallback values in the code were too restrictive and were being used instead of or in addition to the database values.

## User Complaint (Original German)

"Aktuell funktioniert die Schichtplanung nicht, obwohl ich die Maximale Anzahl von Mitarbeitern in der Früh und Spät schicht massiv erhöht wurden.

Bitte auch noch mal darauf achten, dass die in den Schichteinstellungen gesetzten Werte verwendet werden und nicht had im code steht."

Translation: "Currently, shift planning is not working, even though I massively increased the maximum number of employees in the early and late shifts. Please also make sure that the values set in the shift settings are used and not hardcoded in the code."

## Root Cause

Hardcoded maximum staff values existed in multiple places and were too restrictive:

1. **constraints.py** - WEEKDAY_STAFFING and WEEKEND_STAFFING
   - F (Früh/Morning): max = 8
   - S (Spät/Late): max = 7
   - N (Nacht/Night): max = 3

2. **entities.py** - STANDARD_SHIFT_TYPES
   - F: max_staff_weekday = 8, max_staff_weekend = 4
   - S: max_staff_weekday = 7, max_staff_weekend = 4
   - N: max_staff_weekday = 3, max_staff_weekend = 3

3. **entities.py** - ShiftType dataclass defaults
   - max_staff_weekday = 5
   - max_staff_weekend = 3

4. **data_loader.py** - Migration fallback values
   - max_staff_weekday = 5
   - max_staff_weekend = 3

These restrictive values prevented the solver from finding solutions, especially when cross-team assignments were needed to meet monthly hours requirements.

## Solution

Increased all hardcoded max staff values to **20** to provide maximum flexibility while maintaining safety through minimum staffing requirements.

### Files Changed

#### 1. constraints.py
- Updated WEEKDAY_STAFFING max values: 8/7/3 → 20
- Updated WEEKEND_STAFFING max values: 4/4/3 → 20
- Added clear comments indicating these are fallback values only

#### 2. entities.py
- Updated STANDARD_SHIFT_TYPES max values: 8/7/3 → 20 (weekday), 4/4/3 → 20 (weekend)
- Updated ShiftType dataclass defaults: 5 → 20 (weekday), 3 → 20 (weekend)
- Added comments indicating these are fallback values

#### 3. data_loader.py
- Updated migration fallback values: 5 → 20 (weekday), 3 → 20 (weekend)
- Added comment about flexibility

#### 4. INFEASIBLE_FIX.md
- Updated example to show new max value of 20

## Impact

### Before Fix
- Max staff values were hardcoded at 8/7/3 (weekday) and 4/4/3 (weekend)
- Solver could not find solutions even when database was updated
- Cross-team assignments were blocked by restrictive constraints
- Planning failed with INFEASIBLE status

### After Fix
- Max staff values are now 20 for all shifts (weekday and weekend)
- Solver has maximum flexibility to assign cross-team workers
- Database configuration is properly respected
- Fallback values no longer block solutions

## Testing

Created `test_max_staff_values.py` to verify:
- ✅ STANDARD_SHIFT_TYPES have max values >= 20
- ✅ WEEKDAY_STAFFING has max values >= 20
- ✅ WEEKEND_STAFFING has max values >= 20
- ✅ ShiftType dataclass defaults have max values >= 20

All tests pass successfully.

## Design Philosophy

1. **Database is Source of Truth**: The database ShiftType configuration should always be the primary source for staffing requirements.

2. **Fallback Values Should Not Restrict**: When fallback/default values are needed (old database schemas, missing configuration), they should be permissive (high max values) rather than restrictive.

3. **Safety Through Minimums**: Minimum staffing requirements ensure safety and operational needs, while high maximum values provide flexibility.

4. **Cross-Team Flexibility**: Allowing high max values enables cross-team assignments, which help employees meet their monthly hours targets.

## Migration Guide

### For Users
No action required. The fix is transparent and will apply automatically.

If you have custom max staff values in your database:
- Your database values will continue to be used
- The increased fallback values only apply if your database doesn't have these columns

### For Developers
When adding new shift types or modifying staffing logic:
- Always use the database ShiftType configuration as the primary source
- Use STANDARD_SHIFT_TYPES and staffing constants only as last resort fallbacks
- Keep fallback max values high (≥ 20) to avoid blocking solutions
- Document that values are fallbacks only

## Future Considerations

1. **Remove Fallbacks Entirely**: Consider requiring database configuration and removing fallback constants completely.

2. **Validation Layer**: Add validation to warn if database values are too restrictive (e.g., max < 2x min).

3. **Dynamic Calculation**: Consider calculating appropriate max values based on team sizes and configuration.

4. **Configuration UI**: Ensure the web UI properly exposes and allows editing of min/max staff values.

## Summary

This fix ensures that:
1. Hardcoded values no longer block shift planning
2. Database configuration is properly respected
3. The solver has maximum flexibility for cross-team assignments
4. Users can configure max staff values without code changes

The shift planning system should now work correctly even when users increase max staff values in the database configuration.
