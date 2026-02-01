# Shift Sequence Grouping Constraint

## Overview

This document describes the shift sequence grouping constraint implemented to prevent isolated shift types in employee schedules.

## Problem Statement

In the February 2026 schedule, several employees had problematic shift patterns where one shift type appeared isolated in the middle of another shift type:

### Examples of Invalid Patterns

1. **Anna Schmidt (PN002)** - Mo 16.02 to Sa 21.02:
   ```
   S S - F S S
   ```
   - Monday: Spät (S)
   - Tuesday: Spät (S)
   - Wednesday: Free (-)
   - Thursday: Früh (F) ← **Isolated F shift**
   - Friday: Spät (S)
   - Saturday: Spät (S)

2. **Robert Franke (S001)**:
   ```
   S - F S S S S
   ```
   - Single F shift surrounded by S shifts

3. **Max Müller (PN001)**:
   ```
   S - F F S S
   ```
   - Two F shifts between S shifts

4. **Markus Richter (PN011)**:
   ```
   N S S N N N
   ```
   - Two S shifts in the middle of N shifts

5. **Nicole Schröder (PN014)**:
   ```
   S S - F S S
   ```
   - Single F shift between S shifts

## Requirement

**Rule**: When an employee works multiple shift types in a period, they should be properly grouped.

- All days of shift type A should come before OR after all days of shift type B
- No shift type should appear, then disappear, then appear again
- Free days ("-") are allowed and don't break the grouping

### Valid Patterns ✅

- `F F F S S S` - All F shifts grouped, then all S shifts grouped
- `S S S F F F` - All S shifts grouped, then all F shifts grouped
- `F F F - - S S S` - Free days don't matter, shifts still grouped
- `N N N N N` - Single shift type throughout

### Invalid Patterns ❌

- `S S F S S` - F is isolated in the middle
- `S - F S S S` - F appears before S shifts return
- `N S S N N` - S shifts in the middle of N shifts
- `F S F` - Alternating shift types

## Implementation

### Constraint Function

**Location**: `constraints.py`, function `add_shift_sequence_grouping_constraints()`

**Type**: Soft Constraint (penalized but not forbidden)

**Penalty**: 1000 points per violation

### Algorithm

For each employee and each week:

1. Collect all shift assignments for each day in the week
2. For each pair of shift types (A, B):
   - Find all days where shift A could be assigned
   - Find all days where shift B could be assigned
3. Check if any day with shift B falls between two days with shift A
4. If yes, create a penalty:
   - Violation is active if all three shifts are actually assigned
   - Penalty = 1000 points

### Example Detection

Given pattern `S S - F S S` (Mon-Sat):

```
Days with S: [Monday, Tuesday, Friday, Saturday]
Days with F: [Thursday]

Check: Is Thursday between Tuesday and Friday?
→ YES: This is a violation!

Create constraint:
  IF (Tuesday=S AND Thursday=F AND Friday=S)
  THEN penalty = 1000
```

### Code Structure

```python
def add_shift_sequence_grouping_constraints(
    model, employee_active, employee_weekend_shift,
    team_shift, employee_cross_team_shift, 
    employee_cross_team_weekend, employees,
    dates, weeks, shift_codes, teams
):
    """
    Prevent isolated shift types in sequences.
    Returns list of penalty variables.
    """
    
    # For each employee and week
    for emp in employees:
        for week_idx, week_dates in enumerate(weeks):
            # Get shift data for each day
            week_shift_data = [...]
            
            # For each pair of shift types
            for shift_A in shift_codes:
                for shift_B in shift_codes:
                    # Find days with each shift
                    days_with_A = [...]
                    days_with_B = [...]
                    
                    # Check for A-B-A pattern
                    for day_A1 in days_with_A:
                        for day_B in days_with_B:
                            for day_A2 in days_with_A:
                                if day_A1 < day_B < day_A2:
                                    # Create penalty constraint
                                    violation_var = model.NewBoolVar(...)
                                    penalty_var = model.NewIntVar(0, 1000, ...)
                                    model.Add(penalty_var == violation_var * 1000)
                                    penalties.append(penalty_var)
    
    return penalties
```

## Integration

### Solver Integration

The constraint is integrated into the main solver in `solver.py`:

1. **Import** (line 14):
   ```python
   from constraints import add_shift_sequence_grouping_constraints
   ```

2. **Call during constraint setup** (lines 118-122):
   ```python
   print("  - Shift sequence grouping constraints...")
   shift_grouping_penalties = add_shift_sequence_grouping_constraints(
       model, employee_active, employee_weekend_shift, team_shift,
       employee_cross_team_shift, employee_cross_team_weekend,
       employees, dates, weeks, shift_codes, teams)
   ```

3. **Add to objective function** (lines 226-230):
   ```python
   if shift_grouping_penalties:
       print(f"  Adding {len(shift_grouping_penalties)} shift grouping penalties...")
       for penalty_var in shift_grouping_penalties:
           objective_terms.append(penalty_var)  # 1000 per violation
   ```

### Penalty Weight

- **Value**: 1000 points per violation
- **Relative Priority**:
  - Higher than shift hopping (200 points)
  - Higher than weekend consistency (300 points)
  - Higher than consecutive shifts (300-400 points)
  - Equal to weekly shift type diversity (500 points)
  - Lower than night shift consistency (600 points)

This ensures shift grouping is strongly encouraged while still allowing other important constraints to be satisfied.

## Testing

### Verification Steps

1. **Generate a new schedule** for February 2026
2. **Check each employee's schedule** for shift patterns
3. **Verify** no instances of:
   - `A A B A A` patterns (isolated B)
   - `A B A` patterns (B between A's)
   - Any shift type appearing, disappearing, then reappearing

### Expected Results

After implementation:
- Employees should have cleanly grouped shift types within weeks
- Patterns like `S S - F S S` should be eliminated
- Alternative patterns like `F - S S S S` or `S S S - F F` should be preferred

### Example Valid Schedules

**Employee A - Week 1**:
```
Mon  Tue  Wed  Thu  Fri  Sat  Sun
 F    F    F    F    F    -    -
```
All F shifts grouped, weekend off.

**Employee B - Week 2**:
```
Mon  Tue  Wed  Thu  Fri  Sat  Sun
 -    S    S    S    S    S    S
```
Monday off, all S shifts grouped.

**Employee C - Week 3**:
```
Mon  Tue  Wed  Thu  Fri  Sat  Sun
 N    N    -    -    S    S    S
```
N shifts at beginning, S shifts at end (properly grouped).

## Benefits

1. **Improved Schedule Quality**: Employees have more predictable and consistent shift patterns
2. **Better Work-Life Balance**: Grouped shifts make it easier to plan personal life
3. **Compliance**: Ensures shifts follow the stated requirement
4. **Flexibility Maintained**: Soft constraint allows solver to find solutions even if perfect grouping is not possible

## Technical Notes

### Variable Types

All variables involved are `BoolVar` (boolean variables):
- `team_shift[(team_id, week_idx, shift_code)]` - Boolean
- `employee_active[(emp_id, date)]` - Boolean
- `employee_weekend_shift[(emp_id, date)]` - Boolean
- `employee_cross_team_shift[(emp_id, date, shift_code)]` - Boolean

### Constraint Formulation

Uses OR-Tools CP-SAT standard constraint patterns:
- `AddBoolAnd()` to detect when all required conditions are met
- `Add(penalty == violation * constant)` for penalty calculation
- Follows best practices from existing constraints like `add_shift_stability_constraints()`

### Performance

- Constraint is checked per employee per week
- Complexity: O(employees × weeks × shifts²)
- For typical system (15-17 employees, 4 weeks, 3 shifts): ~3000 constraint checks
- Performance impact: Minimal, comparable to existing constraints

## Related Constraints

This constraint works together with other shift stability constraints:

1. **Shift Hopping Prevention** (`add_shift_stability_constraints`):
   - Prevents rapid A→B→A changes over 3 consecutive days
   - Penalty: 200 points

2. **Weekly Shift Type Limit** (`add_weekly_shift_type_limit_constraints`):
   - Limits to max 2 different shift types per week
   - Penalty: 500 points

3. **Weekend Consistency** (`add_weekend_shift_consistency_constraints`):
   - Prevents shift changes from Friday to Saturday/Sunday
   - Penalty: 300 points

The new grouping constraint complements these by ensuring proper grouping within the allowed shift types.

## Future Enhancements

Possible improvements:

1. **Configurable Penalty**: Allow admin to adjust penalty weight
2. **Minimum Group Size**: Require at least N consecutive days of same shift type
3. **Cross-Week Checking**: Detect patterns that span week boundaries
4. **Reporting**: Add validation report showing grouping violations in existing schedules

## References

- **Issue**: February 2026 schedule review
- **Implementation**: PR copilot/update-february-shift-schedule
- **Files Modified**:
  - `constraints.py` - New constraint function
  - `solver.py` - Integration into solver
- **Security Scan**: CodeQL - 0 alerts
- **Code Review**: Completed with feedback addressed
