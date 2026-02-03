# Rest Time Violations - Analysis and Fix

## Problem Statement

The February schedule contained 7 instances of forbidden S→F (Spät→Früh) transitions, which violate the 11-hour minimum rest requirement. These transitions provide only 8 hours of rest between shifts (Spät ends at 21:45, Früh starts at 05:45).

### Violations Found

| Employee | Days | Transition | Rest Time |
|----------|------|------------|-----------|
| Anna Schmidt (PN002) | 22→23 | S→F | 8 hours |
| Max Müller (PN001) | 1→2 | S→F | 8 hours |
| Peter Weber (PN003) | 22→23 | S→F | 8 hours |
| Daniel Koch (PN009) | 15→16 | S→F | 8 hours |
| Sarah Hoffmann (PN008) | 15→16 | S→F | 8 hours |
| Andreas Wolf (PN013) | 8→9 | S→F | 8 hours |
| Maria Lange (S003) | 8→9 | S→F | 8 hours |

## Root Cause Analysis

### Why Did This Happen?

The shift planning system uses OR-Tools CP-SAT solver with a soft constraint approach for rest time violations. This means:

1. **Rest time constraints are "soft"** - violations are allowed but penalized
2. **Multiple competing constraints** - the solver balances many constraints simultaneously
3. **Penalty weights determine priority** - constraints with higher penalties are violated less often

### The Problem

The penalty weights for rest time violations were set too low:
- **Sunday→Monday transitions**: 50 points per violation
- **Weekday transitions**: 500 points per violation

Meanwhile, other constraints had much higher penalties:
- **Shift grouping**: 100,000-500,000 points
- **Minimum consecutive weekdays**: 6,000-8,000 points
- **Shift hopping**: 200 points

This meant the solver could "save" more points by violating rest times than by violating other constraints.

### Example Scenario

Consider a situation where the solver must choose:
- Option A: Violate rest time (500 points) to maintain shift grouping
- Option B: Break shift grouping (100,000 points) to respect rest time

The solver rationally chooses Option A because it minimizes the total penalty.

## Solution

### Fix Applied

Increased rest time penalty weights by 100x:
- **Sunday→Monday transitions**: 50 → **5,000** points
- **Weekday transitions**: 500 → **50,000** points

This ensures rest time violations are now among the most heavily penalized constraints, making them only occur when absolutely necessary for a feasible solution.

### Code Changes

File: `constraints.py`, function `add_rest_time_constraints()`

```python
# OLD (incorrect):
penalty_weight = 50   # Sunday→Monday
penalty_weight = 500  # Weekdays

# NEW (correct):
penalty_weight = 5000   # Sunday→Monday
penalty_weight = 50000  # Weekdays
```

## Prevention Measures

### 1. Automated Validation

The system already includes validation in `validation.py` that checks for rest time violations:

```python
# Check forbidden transitions
if current_shift == "S" and next_shift == "F":
    result.add_violation(
        f"{emp_name} has forbidden transition Spät->Früh on {current.date}->{next_assign.date} (only 8h rest)"
    )
elif current_shift == "N" and next_shift == "F":
    result.add_violation(
        f"{emp_name} has forbidden transition Nacht->Früh on {current.date}->{next_assign.date} (0h rest)"
    )
```

**Recommendation**: Always run validation after generating a schedule and before finalizing it.

### 2. Monitoring Recommendations

1. **Pre-deployment validation**: 
   - Always validate schedules before they go live
   - Review validation report and investigate any violations
   - If violations are found, regenerate the schedule or manually adjust

2. **Regular audits**:
   - Review past schedules monthly for violations
   - Track violation trends over time
   - Investigate if violations increase

3. **Alert system** (future enhancement):
   - Add email/notification when validation finds critical violations
   - Prevent schedule publication if critical violations exist
   - Require manual override with justification

### 3. Constraint Tuning Guidelines

When adding or modifying constraints, follow these guidelines:

**Penalty Weight Hierarchy**:
- **Critical safety/legal requirements**: 50,000+ points
  - Rest time violations (S→F, N→F)
  - Maximum consecutive shifts
  - Legal working hours limits
  
- **Important business rules**: 5,000-10,000 points
  - Minimum consecutive weekday shifts
  - Team consistency
  
- **Optimization preferences**: 100-1,000 points
  - Fairness objectives
  - Preference satisfaction
  - Shift stability

### 4. Testing Protocol

Before deploying constraint changes:

1. **Unit test**: Verify penalty values are correct
2. **Integration test**: Generate sample schedules
3. **Validation test**: Run validation on generated schedules
4. **Regression test**: Compare with previous schedules to ensure no degradation

## Future Enhancements

### Consider Hard Constraints

Currently, rest time violations are soft constraints (allowed but penalized). Consider making them **hard constraints** (never allowed) if:

1. Legal requirements mandate it
2. Violations are completely unacceptable
3. Feasibility testing shows solutions always exist

To convert to hard constraint, replace penalty logic with:

```python
# Hard constraint: S→F and N→F are forbidden
for i_today, today_shift_code in enumerate(today_shift_codes):
    for i_tomorrow, tomorrow_shift_code in enumerate(tomorrow_shift_codes):
        if (today_shift_code == "S" and tomorrow_shift_code == "F") or \
           (today_shift_code == "N" and tomorrow_shift_code == "F"):
            # Add constraint: these two shifts cannot both be true
            model.Add(today_shifts[i_today] + tomorrow_shifts[i_tomorrow] <= 1)
```

**Caution**: Hard constraints can make the problem infeasible if the solution space is too constrained.

### Visualization

Add a visual indicator in the UI to highlight rest time violations:
- Color-code transitions: Red for forbidden, Yellow for suboptimal, Green for good
- Show rest hours between consecutive shifts
- Highlight employees with violations in the schedule view

## Summary

The rest time violations were caused by insufficient penalty weights in the constraint solver. By increasing penalties 100x, rest time violations now have the appropriate priority and will only occur when absolutely necessary for feasibility. Combined with existing validation and proposed monitoring, this ensures similar issues are caught and prevented in the future.
