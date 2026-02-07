# Shift Planning Rules Review - Summary

**Date:** 2026-02-07  
**Issue:** Review of shift planning rules and removal of hard-coded values

## Overview

This document summarizes the review and updates made to the shift planning rules based on user feedback regarding hard-coded values vs. database-driven configuration.

## Issues Addressed

### ✅ H2 vs H10 - Team Rotation Contradiction

**Finding:** No contradiction - the code is already database-driven.

**Change:** 
- Updated documentation to clarify that rotation patterns are loaded from `RotationGroups` table in the database
- F→N→S is used as a DEFAULT FALLBACK pattern when no database configuration exists
- Renamed `ROTATION_PATTERN` to `DEFAULT_ROTATION_PATTERN` for clarity

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md` 
- `SHIFT_PLANNING_RULES_EN.md`
- `constraints.py` (comments)

### ✅ H3 - Minimum Staffing Values

**Finding:** Values are NOT hard-coded - they are dynamically read from the database.

**Change:** 
- Fixed documentation which incorrectly showed hard-coded values (F≥4, S≥3, N≥3, weekend≥2)
- Clarified that actual values come from `ShiftType.min_staff_weekday` and `ShiftType.min_staff_weekend`

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`

### ✅ H4 - Forbidden Transitions

**Finding:** Transitions (S→F, N→F) are based on shift timing and 11-hour rest rule, NOT derived from rotation groups.

**Change:**
- Clarified in documentation that forbidden transitions are determined by shift start/end times
- Noted these are SOFT constraints (penalty-based) not HARD constraints
- Removed unused `FORBIDDEN_TRANSITIONS` dict from code
- Updated documentation to show it's a soft constraint with penalties of 50,000 (weekday) and 5,000 (Sunday-Monday)

**Technical Detail:**
- S→F: Spät ends 21:45, Früh starts 05:45 = only 8 hours rest (violates 11h rule)
- N→F: Nacht ends 05:45, Früh starts 05:45 = 0 hours rest (violates 11h rule)

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`
- `constraints.py` (removed dict, updated comments)

### ⚠️ H7 - TD (Tagdienst) Restriction

**Finding:** Special TD constraint exists but should be obsolete per user feedback.

**Change:**
- Added deprecation notice to the TD constraint function
- Documented that TD/BMT/BSB should be managed as regular shift types
- Kept the code functional for backward compatibility
- Marked rule as "VERALTET" (deprecated) in documentation

**Recommendation:** 
Future implementations should:
1. Create TD/BMT/BSB as regular shift types in `ShiftType` management
2. Assign them to teams via `TeamShiftAssignments`
3. Let them follow normal rotation and staffing rules

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`
- `constraints.py` (added deprecation notice)

### ✅ H8 - Maximum Weekly Hours

**Finding:** There is NO hard 48h weekly maximum in the code. Documentation was misleading.

**Change:**
- Corrected documentation to show actual implementation:
  - HARD constraint: 192h monthly minimum
  - SOFT constraint: Proportional target calculated as `(weekly_hours/7) × calendar_days`
  - NO hard weekly maximum
- Renamed rule from "Maximale Wochenstunden" to "Mindeststunden pro Monat"

**Example Calculations:**
- January (31 days): Target = 48h/7 × 31 = 212.57h
- February (28 days): Target = 48h/7 × 28 = 192h

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`

### ✅ Soft Rule 4 & 8 - Rotation Order

**Finding:** Rotation is already database-driven.

**Change:**
- Updated documentation to clarify rotation sequence comes from `RotationGroups` database
- F→N→S mentioned as default fallback, not hard requirement

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`

### ✅ Soft Rule 10 - Target Hours Calculation

**Finding:** 192h is hard minimum, but proportional target is dynamically calculated.

**Change:**
- Clarified documentation:
  - 192h/month = hard minimum constraint
  - Proportional target = soft constraint, calculated as `(weekly_hours/7) × calendar_days`
  - No fixed monthly value

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`

### ✅ Soft Rule 11 - Weekly Shift Type Limit

**Finding:** Code implements maximum of 2 different shift types per week, not "2-3".

**Change:**
- Fixed documentation from "Max. 2-3" to "Max. 2"
- Matches code implementation: `max_shift_types_per_week: int = 2` (line 2282)

**Files Updated:**
- `SCHICHTPLANUNGS_REGELN.md`
- `SHIFT_PLANNING_RULES_EN.md`

## Code Changes Summary

### constraints.py

1. **Removed unused constants:**
   - Deleted `FORBIDDEN_TRANSITIONS` dict (was defined but never used)
   
2. **Renamed constants for clarity:**
   - `ROTATION_PATTERN` → `DEFAULT_ROTATION_PATTERN` (emphasizes it's a fallback)

3. **Added clarifying comments:**
   - Explained that forbidden transitions are based on shift timing, not rotation groups
   - Clarified that rotation patterns are database-driven with fallback
   - Added note that min/max staffing is always from database

4. **Added deprecation notice:**
   - Marked `add_td_constraints()` function as deprecated/optional
   - Explained alternative approach using regular shift types

### Documentation Files

1. **SCHICHTPLANUNGS_REGELN.md** (German)
   - Updated all hard constraint descriptions (H2, H3, H4, H7, H8)
   - Merged H10 into H2 (same rule, different description)
   - Updated soft constraints (4, 10, 11)
   - Added file path references for all rules

2. **SHIFT_PLANNING_RULES_EN.md** (English)
   - Applied same changes as German version
   - Consistent terminology and structure

## Testing

✅ Tested database rotation loading - works correctly  
✅ Verified fallback to default pattern - works correctly  
✅ Verified constant rename - no errors  
✅ Documentation now accurately reflects code behavior

## Recommendations for Future

1. **Consider removing TD special handling:**
   - TD/BMT/BSB should be managed as regular shift types
   - Would simplify the codebase significantly
   - Current implementation is maintained for backward compatibility

2. **Rotation Groups:**
   - Continue using database-driven approach
   - Default F→N→S pattern provides good fallback

3. **Staffing Requirements:**
   - Continue dynamic configuration from database
   - Provides maximum flexibility for different shift types

4. **Hours Calculation:**
   - Current proportional calculation is flexible and fair
   - Adapts to different month lengths automatically

## Files Modified

1. `/home/runner/work/Dienstplan/Dienstplan/SCHICHTPLANUNGS_REGELN.md`
2. `/home/runner/work/Dienstplan/Dienstplan/SHIFT_PLANNING_RULES_EN.md`
3. `/home/runner/work/Dienstplan/Dienstplan/constraints.py`

## Conclusion

All identified issues have been addressed. The system is already highly dynamic and database-driven. Documentation has been updated to accurately reflect the implementation. No hard-coded values remain except for necessary defaults and fallbacks.

The main recommendation is to consider phasing out the special TD handling in favor of managing TD/BMT/BSB as regular shift types, which would align with user expectations and simplify the system.

---

**Author:** GitHub Copilot  
**Reviewer:** TimUx  
**Status:** Complete
