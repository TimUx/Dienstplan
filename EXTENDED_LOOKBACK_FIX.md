# Extended Lookback Fix for Cross-Month Consecutive Shift Violations

## Problem Statement

The consecutive shift limit (e.g., maximum 6 consecutive days) was not being properly enforced when scheduling spanned across month boundaries. Employees could accumulate very long consecutive shift chains (16+ days) when the limit was 6 days.

### Example Scenario

- **February Planning**: Lisa Meyer works Feb 1-22 (22 consecutive days)
  - Constraint detects violation, but solver accepts penalty
  - Shifts are saved to database
  
- **March Planning**: System plans Mar 1-31, extends to Feb 23 to complete boundary week
  - Loads previous shifts: Only Feb 17-22 (last 6 days)
  - **Missing**: Feb 1-16 (first 16 days of the chain)
  - Plans Feb 23-Mar 15 with more consecutive shifts
  - Constraint only sees 6 + new days, not the full 22 + new days

- **Result**: Lisa ends up with 16+ consecutive shifts across weeks 9-10 (Feb 23 - Mar 10)

## Root Cause

The lookback period was limited to `max_consecutive_days` (typically 6 days):

```python
# OLD CODE
lookback_start = extended_start - timedelta(days=max_consecutive_limit)
lookback_end = extended_start - timedelta(days=1)
```

This meant:
1. Each planning period only examined the most recent `max_consecutive_days` before it started
2. Longer consecutive chains from earlier in the previous month were invisible
3. Each month's planning could accept "small" violations (6-8 days)
4. These "small" violations accumulated into very large violations (16+ days) across months

## Solution

Implemented **dynamic extended lookback** that adapts to actual employee shift patterns:

### Two-Pass Loading Approach

#### Pass 1: Initial Lookback (Standard)
```python
initial_lookback_start = extended_start - timedelta(days=max_consecutive_limit)
initial_lookback_end = extended_start - timedelta(days=1)
# Load shifts from this period for all employees
```

#### Pass 2: Extended Lookback (Conditional)
```python
# For each employee with consecutive shifts in initial lookback:
if employee has max_consecutive_limit consecutive days ending at extended_start-1:
    # Chain might extend further back - need more data
    extended_lookback_start = extended_start - timedelta(days=60)
    extended_lookback_end = initial_lookback_start - timedelta(days=1)
    # Load additional shifts from this extended period
```

### Why 60 Days?

The maximum lookback of 60 days (approximately 2 months) balances:

1. **Violation Detection**: Long enough to catch realistic violation chains (even 10x typical limits)
2. **Database Performance**: Limits query scope to prevent excessive load
3. **Regulatory Focus**: Health/safety rules focus on recent consecutive work, not months-old patterns
4. **Practical Limit**: Violations beyond 60 days would have been severely penalized in their own planning period

### Extension Trigger Logic

```python
consecutive_days = 0
check_date = extended_start - timedelta(days=1)

for _ in range(max_consecutive_limit):
    if employee_worked_shift(check_date):
        consecutive_days += 1
        check_date -= timedelta(days=1)
    else:
        break  # Chain broken

# Extend if we found max_consecutive_limit consecutive days without breaking
if consecutive_days == max_consecutive_limit:
    employees_to_extend.append(emp_id)
```

Key insight: If we found exactly `max_consecutive_limit` consecutive days in the initial lookback, the chain might extend further back. We need more data to assess the full violation.

## Implementation

### Files Modified

**web_api.py** (lines 3115-3220)
- Added dynamic lookback extension logic
- Two-pass database query approach
- Parameterized queries for SQL injection prevention
- Detailed logging of extension activity

### Security Considerations

✅ **SQL Injection Prevention**: Used parameterized queries with placeholders
```python
placeholders = ','.join('?' * len(employees_to_extend))
query = f"""... WHERE ... AND sa.EmployeeId IN ({placeholders}) ..."""
params = [start, end] + employees_to_extend
cursor.execute(query, params)
```

✅ **Performance**: Limited maximum lookback to 60 days
✅ **Database Load**: Only extends for employees who need it (not all employees)

## Testing

### New Test: test_long_chain_across_months.py

Demonstrates the fix with a realistic scenario:

```python
# Simulate employee with 22 consecutive days in Feb
previous_employee_shifts = {
    (employee.id, date(2026, 2, day)): "S" 
    for day in range(1, 23)
}

# Planning March with these previous shifts
# Constraint now sees all 22 days, not just the last 6
# Result: Much higher penalty (19200) that discourages long chains
```

### Test Results

✅ **test_long_chain_across_months.py**: PASS  
✅ **test_cross_month_consecutive.py**: PASS (existing test)  
✅ **test_max_consecutive_days.py**: PASS (existing test)  
✅ **CodeQL Security Scan**: No vulnerabilities  
✅ **Code Review**: All feedback addressed (3 iterations)

## Impact

### Before Fix
- Employee could work 22 days in Feb (penalty accepted)
- March planning only saw last 6 days, planned 10 more days
- **Total: 32+ consecutive days** with limited penalty visibility

### After Fix
- Employee works 22 days in Feb (penalty accepted)
- March planning sees **all 22 days**, not just 6
- Planning 10 more days generates **much higher penalties**
- Solver strongly discouraged from continuing the chain
- **Result: Proper enforcement across month boundaries**

## Example Log Output

```
INFO: Planning for 2026-03-01 to 2026-03-31
INFO: Extended to complete week: 2026-02-23 to 2026-03-31
INFO: Loaded 144 previous shift assignments for consecutive days checking
INFO: Previous shifts date range: 2026-02-17 to 2026-02-22
INFO: Extending lookback for 3 employees with long consecutive chains
INFO: Previous shifts date range: 2026-01-24 to 2026-02-22
INFO: Extended lookback for 3 employees to capture full consecutive chains
```

## Future Enhancements

1. **Adaptive Lookback**: Adjust max_lookback_days based on historical patterns
2. **Violation Reporting**: Add UI warning when extended lookback detects long chains
3. **Performance Optimization**: Cache extended lookback data for subsequent planning periods
4. **Analytics**: Track how often extended lookback is triggered to tune thresholds

## Related Documentation

- `CROSS_MONTH_CONSECUTIVE_FIX.md` - Original cross-month boundary checking
- `MAX_CONSECUTIVE_DAYS_FIX.md` - Per-shift-type consecutive days constraints
- `TOTAL_CONSECUTIVE_DAYS_FIX.md` - Total consecutive days across all shift types

## Summary

This fix ensures that consecutive shift limits are properly enforced across month boundaries by dynamically extending the lookback period when needed. It prevents scenarios like Lisa Meyer's 16 consecutive shifts (limit: 6) by ensuring the constraint sees the full violation chain, not just the most recent days.

**Status**: ✅ Complete, Tested, and Deployed  
**Date**: 2026-02-12  
**Issue**: Lisa Meyer 16 consecutive shifts in KW 9-10 despite 6-day limit
