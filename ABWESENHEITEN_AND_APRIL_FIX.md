# Fix Summary - Abwesenheiten Rename and April Month Boundary

## Issues Addressed

### Issue 1: Statistics Column Rename and Categorization
**Request**: Rename "Fehltage" to "Abwesenheiten" and display absences categorized by type.

**Solution**:
- Updated API endpoint `get_dashboard_stats()` in `web_api.py` to query and return absence data grouped by type
- Modified frontend in `wwwroot/js/app.js` to display "Abwesenheiten" with type breakdown
- Absence types are now shown with their display names:
  - AU → Krank/AU
  - U → Urlaub  
  - L → Lehrgang
- Updated documentation in README.md and BENUTZERHANDBUCH.md

**Example Output**: 
```
Max Müller: 5 Tage (Urlaub: 3, Krank/AU: 2)
```

### Issue 2: April 2026 Planning INFEASIBLE Error
**Problem**: When planning April 2026, the solver returned INFEASIBLE with warnings:
```
WARNING: Skipping conflicting locked shift for team 1, week 0
  Existing: N, Attempted: S (from employee 2 on 2026-03-30)
```

**Root Cause**:
- April 1, 2026 is a Wednesday
- Planning extends back to Monday, March 30 (to complete the week)
- Week 0 spans March 30 - April 5 (crosses month boundary)
- Locked employee shifts from March exist in the database
- Different team members worked different shifts on different days during the overlapping week
- The team-based model requires all team members to work the SAME shift for the ENTIRE week
- System tried to lock team to multiple conflicting shifts → INFEASIBLE

**Solution**:
Added a check in `model.py` line 264-274 to detect when a week spans month boundaries:
```python
week_spans_boundary = any(
    wd < self.original_start_date or wd > self.original_end_date 
    for wd in week_dates
)

if week_spans_boundary:
    # Skip team lock - use only employee-level locks
    continue
```

This ensures:
- Weeks that contain dates outside the original planning period do NOT get team-level locks
- Only employee-level locks are applied for boundary weeks
- No conflicting team constraints are created
- Solver can find feasible solutions

## Files Changed

### Backend
- `web_api.py`: Updated absence statistics query and data structure
- `model.py`: Added month boundary detection for locked shifts

### Frontend  
- `wwwroot/js/app.js`: Updated statistics display with categorization

### Documentation
- `README.md`: Updated statistics description
- `BENUTZERHANDBUCH.md`: Updated statistics section

### Tests
- `test_april_2026_boundary_fix.py`: New test verifying April planning works

## Testing

### New Test
✓ `test_april_2026_boundary_fix.py` - Verifies:
- Week 0 has no team-level locks when it spans month boundary
- April 2026 planning completes successfully
- No INFEASIBLE errors

### Existing Tests Verified
✓ `test_february_2026_conflict_fix.py` - Still passes, confirming no regression

### Security Review
✓ CodeQL analysis: 0 alerts found (Python and JavaScript)

## Impact

### User-Visible Changes
1. Statistics page now shows "Abwesenheiten" instead of "Fehltage"
2. Absence days are broken down by type (AU, U, L)
3. April 2026 (and similar month boundaries) can now be planned without INFEASIBLE errors

### Technical Benefits
1. More informative absence statistics
2. Robust handling of month boundaries in shift planning
3. Prevents solver conflicts at week overlaps
4. No breaking changes to existing functionality

## Minimal Change Approach

All changes were surgical and targeted:
- API: Changed one SQL query to add GROUP BY Type
- Frontend: Updated one section to display categorized data
- Solver: Added one boundary check before creating team locks
- No changes to database schema or core business logic
- All existing tests continue to pass
