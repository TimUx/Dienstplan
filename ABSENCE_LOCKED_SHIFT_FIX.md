# Fix: Absence and Locked Shift Conflict Resolution

## Problem

When planning shifts for March 2026, the system encountered an INFEASIBLE error when:
1. An employee had an absence (AU) from March 1-8
2. The same employee had a locked shift on March 1 from February planning (cross-month week)

This created contradictory constraints:
- **Locked shift** forces `employee_active[emp_id, March 1] = 1` (must work)
- **Absence** forces `employee_active[emp_id, March 1] = 0` (cannot work)
- CP-SAT solver cannot satisfy both → **INFEASIBLE**

## Root Cause

The system was applying locked shifts from previous planning periods without checking for conflicts with absences. When a week spans across months, employees may have locked shifts from the previous month's planning that conflict with absences entered for the new month.

## Solution

Added conflict detection in `model.py` to check for absences **before** applying locked constraints. When a conflict is detected:
1. The locked constraint is skipped (absence takes precedence)
2. A warning message is printed to inform the user
3. The model continues without the conflicting constraint

### Implementation

#### 1. Helper Methods (DRY Principle)
```python
def _employee_has_absence_on_date(self, emp_id: int, check_date: date) -> bool:
    """Check if an employee has an absence on a specific date."""
    return any(
        abs.employee_id == emp_id and abs.overlaps_date(check_date)
        for abs in self.absences
    )

def _employee_has_absence_in_week(self, emp_id: int, week_dates: List[date]) -> bool:
    """Check if an employee has an absence on any day in a given week."""
    return any(
        self._employee_has_absence_on_date(emp_id, d)
        for d in week_dates
    )
```

#### 2. Conflict Detection for Locked Employee Shifts
```python
for (emp_id, d), shift_code in self.locked_employee_shift.items():
    if self._employee_has_absence_on_date(emp_id, d):
        print(f"WARNING: Skipping locked shift for employee {emp_id} on {d}")
        print(f"  Reason: Employee has absence on this date (absence overrides locked shift)")
        continue  # Skip this lock to avoid infeasibility
    # ... apply constraint
```

#### 3. Conflict Detection for Locked Weekend Work
```python
for (emp_id, d), is_working in self.locked_employee_weekend.items():
    if self._employee_has_absence_on_date(emp_id, d):
        if is_working:
            print(f"WARNING: Skipping locked weekend work for employee {emp_id} on {d}")
            print(f"  Reason: Employee has absence on this date (absence overrides locked weekend)")
        continue  # Skip this lock (absence already enforces non-working)
    # ... apply constraint
```

#### 4. Conflict Detection for Locked TD Assignments
```python
for (emp_id, week_idx), has_td in self.locked_td.items():
    if has_td:
        week_dates = self.weeks[week_idx] if week_idx < len(self.weeks) else []
        weekday_dates = [d for d in week_dates if d.weekday() < 5]
        
        if self._employee_has_absence_in_week(emp_id, weekday_dates):
            print(f"WARNING: Skipping locked TD for employee {emp_id} in week {week_idx}")
            print(f"  Reason: Employee has absence this week (absence overrides locked TD)")
            continue  # Skip this lock to avoid infeasibility
    # ... apply constraint
```

## Testing

Created comprehensive test suite in `test_absence_locked_shift_conflict.py`:

### Test 1: Absence Overrides Locked Shift (Weekday)
- Employee has absence on March 1-3
- Locked shift exists on March 1 from previous planning
- ✓ Model creation succeeds
- ✓ Warning message displayed
- ✓ No constraint added for conflicting date

### Test 2: Absence Overrides Locked Weekend Work
- Employee has absence on March 1-2
- Locked weekend work exists on March 1
- ✓ Model creation succeeds
- ✓ Warning message displayed
- ✓ No constraint added for conflicting date

### Test 3: Absence Overrides Locked TD Assignment
- Employee has absence on March 3-5
- Locked TD exists for week 0
- ✓ Model creation succeeds
- ✓ Warning message displayed
- ✓ No constraint added for conflicting week

All tests pass successfully!

## Benefits

1. **Prevents INFEASIBLE errors**: System no longer fails when absences conflict with locked shifts
2. **User-friendly**: Clear warning messages inform users about skipped locks
3. **Correct behavior**: Absences correctly take precedence over locked shifts
4. **Consistent**: Uses same pattern as existing team-level conflict handling
5. **Maintainable**: Helper methods reduce code duplication
6. **Safe**: Existing tests still pass, no regressions

## Files Changed

1. `model.py`: Added helper methods and conflict detection logic
2. `test_absence_locked_shift_conflict.py`: New test file with comprehensive test coverage

## Example Output

When a conflict is detected, users see:
```
WARNING: Skipping locked shift for employee 1 on 2026-03-01
  Reason: Employee has absence on this date (absence overrides locked shift)
```

This clearly communicates that:
- The locked shift is being skipped
- The reason for skipping
- Absence takes precedence

## Security

- CodeQL scan: ✓ No security issues found
- No sensitive data handling
- No new vulnerabilities introduced

## Backward Compatibility

- ✓ Existing functionality preserved
- ✓ Existing tests pass
- ✓ No breaking changes
- ✓ Only adds safety checks
