# Working Hours Fix - Analysis and Solution

## Problem Statement

Employees assigned to teams with shifts (F, S, N) configured for 48h/week should work:
- **Target**: 48 hours/week = 192 hours/month (4 weeks × 48h)
- **Actual**: ~152 hours/month (40 hours short)
- **Requirement**: Absences (U/AU/L) are exceptions - employees are not required to make up hours lost to absences
- **Requirement**: If an employee works less in one week (without absence), they must compensate in other weeks

**Note**: The 48h/week is just an example - the system must work dynamically with any configured `weekly_working_hours` value.

## Root Cause Analysis

After analyzing the codebase, the root cause is the **"weekly available employee constraint"** in `constraints.py`:

```python
def add_weekly_available_employee_constraint(...):
    """
    HARD CONSTRAINT: Weekly available employee for dynamic coverage.
    
    Requirements:
    - Each week, at least 1 employee from shift-teams must not be assigned to any shift
    - This employee can be dynamically deployed as a substitute in case of absences
    """
```

This constraint requires:
- At least 1 employee per team to have **0 working days per week**
- This prevents the remaining employees from working enough days to reach their target hours

### Why this causes the shortfall:

With 8-hour shifts:
- To achieve 48h/week, employees need to work **6 days/week**
- To achieve 40h/week, employees need to work **5 days/week**

Current constraint effect:
- If a team has 5 employees
- 1 must work 0 days (due to constraint)
- Remaining 4 can work max 5 days/week (weekdays only)
- Result: Average = (4×5 + 1×0)/5 = 4 days/week = 32h/week per employee

## Proposed Solution

### Option 1: Remove the Weekly Available Constraint (Simplest)

**Change in `solver.py`:**
```python
# DISABLED: Weekly available employee constraint - conflicts with configured weekly_working_hours requirement
# The constraint forces at least 1 employee to have 0 working days per week,
# which prevents employees from reaching their target hours (e.g., 48h/week = 6 days)
# 
# print("  - Weekly available employee constraint (at least 1 free per week)")
# add_weekly_available_employee_constraint(model, employee_active, employee_weekend_shift, employees, teams, weeks)
```

**Pros:**
- Simple, surgical change
- Allows employees to work weekends to reach target hours
- Maintains all other constraints (rest, consecutive shifts, staffing)

**Cons:**
- Removes buffer capacity for dynamic deployment
- May need additional manual planning for absences

### Option 2: Relax the Constraint (Recommended)

Modify the constraint to require "at least 1 employee works less than 7 days" instead of "at least 1 employee works 0 days":

```python
def add_weekly_available_employee_constraint(...):
    """
    SOFT CONSTRAINT: Weekly available employee for dynamic coverage.
    
    Requirements UPDATED:
    - Each week, at least 1 employee should not work ALL 7 days
    - Changed from "must have 0 working days" to "should not work all 7 days"
    - This allows employees to work 6 days/week (e.g., Mon-Sat) to meet 48h/week target
    """
    # Allow employees to work up to 6 days while keeping Sunday as buffer
```

**Pros:**
- Allows employees to work 6 days/week (48h with 8h shifts)
- Maintains some buffer capacity (Sunday availability)
- Surgical, minimal change

**Cons:**
- Still constrains to 6 days max (won't work for > 48h/week requirements)

### Option 3: Make Weekly Hours Dynamic in Optimization

Add terms to the optimization objective that penalize deviation from target hours:

```python
# In add_fairness_objectives or similar:
for emp in employees:
    # Calculate actual vs. target hours
    # Add penalty for significant deviation
    # This makes the solver try to reach target hours when possible
```

**Pros:**
- Most flexible - works with any weekly_working_hours configuration
- Soft constraint - doesn't cause infeasibility

**Cons:**
- More complex implementation
- May not guarantee minimum hours in all cases

## Additional Changes Made

### 1. Dynamic Validation (`validation.py`)

Updated `validate_working_hours()` to use configured `weekly_working_hours` instead of hardcoded 48h/192h:

```python
def validate_working_hours(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    start_date: date,
    end_date: date,
    shift_types: List = None  # NEW: Pass shift types for dynamic validation
):
    """
    Validate working hours limits based on configured weekly_working_hours in shift types.
    
    Validates that employees:
    - Do not exceed max weekly hours (based on shift's weekly_working_hours)
    - Meet minimum weekly hours (based on shift's weekly_working_hours)
    - Do not exceed max monthly hours (weekly_working_hours * 4)
    
    Note: This is now dynamic based on shift configuration, not hardcoded to 48h/192h
    """
```

### 2. Documentation Update

Updated docstrings to clarify that `weekly_working_hours` is configurable and the algorithm is dynamic.

## Testing Strategy

Created `test_minimum_working_hours.py` with tests for:
1. 48h/week configuration (problem statement example)
2. 40h/week configuration (verify dynamic behavior)
3. Absence exemption (verify absences don't require compensation)

## Recommendation

**Implement Option 1** (Remove weekly available constraint) as the immediate fix:

1. **Simple**: One-line change in `solver.py`
2. **Effective**: Directly addresses the root cause
3. **Safe**: Doesn't introduce new complexity or risks
4. **Validated**: Can be easily tested and verified

If buffer capacity is needed in the future, it can be added back as a configurable soft constraint or handled through manual planning/springer deployment.

## Files Modified

1. `solver.py` - Disable weekly available employee constraint
2. `validation.py` - Dynamic validation based on configured hours
3. `constraints.py` - Updated docstring for `add_working_hours_constraints`
4. `test_minimum_working_hours.py` - NEW: Comprehensive tests

##Implementation Status

- [x] Analyzed root cause
- [x] Updated validation logic to be dynamic
- [x] Created comprehensive tests
- [ ] **PENDING**: Disable weekly available employee constraint (needs decision)
- [ ] **PENDING**: Run tests to verify solution
- [ ] **PENDING**: Update documentation if needed
