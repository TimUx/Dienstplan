# March 2026 Planning INFEASIBLE Fix

## Problem Statement

When planning shifts for March 2026, the system encountered an INFEASIBLE error:
```
INFEASIBLE - no solution found within time limit
constraint #15178: linear { vars: 9362 coeffs: 1 domain: 4 domain: 5 }
```

### Environment
- **Planning Period**: March 1-31, 2026 (extends to Feb 23 - Apr 5, 42 days, 6 weeks)
- **Employees**: 15 employees in 3 teams (5 members per team)
- **Shift Configuration**:
  - F (Frühschicht): min 4, max 8 staff
  - S (Spätschicht): min 3, max 6 staff  
  - N (Nachtschicht): min 3, max 3 staff ← **KEY CONSTRAINT**
- **Rotation**: F → N → S (teams rotate weekly)
- **Minimum Hours**: 192h per month (HARD constraint)

### What Worked
- **February 2026**: Planning succeeded (5 weeks)
- **Other months**: Generally worked fine

### What Failed
- **March 2026**: Planning failed with INFEASIBLE (6 weeks)

## Root Cause Analysis

### The Constraint Conflict

The INFEASIBLE error was caused by an impossible combination of constraints:

1. **Team Size vs N Shift Maximum**
   - Teams have 5 members
   - N shift allows maximum 3 staff per day
   - Only 3 of 5 team members can be active during N week

2. **Minimum Hours Requirement (HARD)**
   - Every employee MUST work at least 192h per month
   - This was enforced as a HARD constraint (blocking feasibility)

3. **Weekly Shift Consistency (HARD)**
   - Employees must work the SAME shift type throughout each week
   - An N-team member who is inactive on Monday cannot work N on Tuesday and switch to F on Wednesday

4. **Cross-Team Capacity Limits**
   - When 2 N-team members are inactive, they need cross-team work to meet 192h
   - But cross-team slots are limited by other teams' max staffing
   - Combined with weekly consistency, finding valid assignments becomes impossible

### The Perfect Storm

In March 2026 (6 weeks), each team works N shift for exactly 2 weeks:

| Week | Team 1 | Team 2 | Team 3 |
|------|--------|--------|--------|
| 0    | F      | N      | S      |
| 1    | N      | S      | F      |
| 2    | S      | F      | N      |
| 3    | F      | N      | S      |
| 4    | N      | S      | F      |
| 5    | S      | F      | N      |

During each N week:
- 3 team members are active (N shift)
- 2 team members are inactive (can't work N, it's full)
- Those 2 members lose 56h that week
- To meet 192h minimum over 6 weeks, they MUST do cross-team work
- But cross-team capacity + weekly consistency creates conflicts

### Why February Worked

February 2026 has only 5 weeks, creating slightly different rotation patterns:
- Some teams get 1 N week, others get 2 N weeks
- Less uniform pressure on cross-team capacity
- Solver found feasible solutions more easily

## Solution

Changed the **192h minimum hours constraint from HARD to SOFT** with a very high penalty (100x).

### Implementation

**File**: `constraints.py`
**Function**: `add_working_hours_constraint()`
**Line**: ~3040

**Before (HARD constraint)**:
```python
min_hours_scaled = 1920  # 192h × 10
model.Add(sum(total_hours_terms) >= min_hours_scaled)
```

**After (SOFT constraint with high penalty)**:
```python
min_hours_scaled = 1920  # 192h × 10

# Create shortage variable
min_hours_shortage = model.NewIntVar(0, min_hours_scaled, 
                                      f"emp{emp.id}_min_hours_shortage")
model.Add(min_hours_shortage >= min_hours_scaled - sum(total_hours_terms))
model.Add(min_hours_shortage >= 0)

# Add to soft objectives with VERY HIGH penalty (100x)
soft_objectives.append(min_hours_shortage * 100)
```

### Why This Works

1. **Preserves Business Intent**
   - The very high penalty (100x) ensures the solver tries extremely hard to meet 192h
   - In normal scenarios, employees will still meet 192h
   
2. **Allows Physical Feasibility**
   - When meeting 192h is physically impossible (N max = 3, team size = 5, weekly consistency)
   - The system remains feasible instead of blocking
   
3. **Enables Monitoring**
   - Administrators can see which employees are below 192h
   - They can investigate root causes (capacity constraints, absences, etc.)
   - They can take corrective action (adjust shift max, add employees, etc.)

### Penalty Weight Rationale

The penalty is set to 100x, which is:
- **Higher than** most soft constraints (overstaffing, understaffing, fairness)
- **Equal to** the target hours shortage penalty (primary objective)
- **Lower than** constraint violations that must be avoided (rest time, rotation order)

This creates a hierarchy:
1. Physical constraints (HARD): Must always be satisfied
2. Minimum hours (SOFT, 100x): Extremely high priority, but can be violated if impossible
3. Target hours (SOFT, 100x): Same priority as minimum
4. Other objectives (SOFT, 1-50x): Lower priority

## Testing

### Test Cases

1. **March 2026 Scenario** (`test_march_2026_fix.py`)
   - Verifies March 2026 is now FEASIBLE
   - Checks that N shift never exceeds max (3 staff)
   - Confirms solution exists

2. **Minimum Hours Soft Constraint** (`test_minimum_hours_soft_constraint.py`)
   - Verifies constraint is soft, not hard
   - Tests extreme scenarios where 192h is impossible
   - Confirms February 2026 still works

### Test Results

```bash
cd /home/runner/work/Dienstplan/Dienstplan
python test_march_2026_fix.py
```

**Expected Output**:
```
✓ Solution found with 532 assignments
```

## Impact

### What Changed
- **March 2026 planning**: Now FEASIBLE ✓
- **192h enforcement**: Still enforced via very high penalty (almost always met)
- **Capacity conflicts**: No longer block the entire planning process

### What Didn't Change
- **February 2026 planning**: Still works ✓
- **Other constraints**: All remain unchanged
- **Business logic**: 192h is still the target, just not absolutely blocking

### Monitoring

Administrators should monitor employee hours and investigate cases where employees are below 192h:
- Check shift capacity settings (is N max too restrictive?)
- Review team sizes (do teams have enough members?)
- Consider absences (did absences reduce available hours?)
- Adjust configuration if needed

## Alternative Solutions Considered

### 1. Increase N Shift Maximum
- **Pro**: Would allow more N-team members to be active
- **Con**: Violates business requirement (N shift needs only 3 staff)
- **Decision**: Rejected - violates actual staffing needs

### 2. Reduce Team Size
- **Pro**: 3-member teams would fit N shift max perfectly
- **Con**: Violates organizational structure
- **Decision**: Rejected - teams are organizational units

### 3. Remove Weekly Consistency
- **Pro**: Would allow flexible day-by-day assignments
- **Con**: Violates business requirement (team-based planning)
- **Decision**: Rejected - core requirement

### 4. Make Minimum Staffing Soft
- **Pro**: Would reduce constraint pressure
- **Con**: Could lead to understaffed shifts (safety issue)
- **Decision**: Rejected - staffing minimums are critical

### 5. Make 192h Soft (CHOSEN)
- **Pro**: Preserves all other constraints, allows feasibility
- **Pro**: Very high penalty ensures 192h is met when possible
- **Pro**: Provides visibility when 192h is unachievable
- **Con**: Requires administrator monitoring
- **Decision**: ACCEPTED - best balance of flexibility and enforcement

## Summary

The March 2026 INFEASIBLE error was caused by an impossible combination of:
- Team size (5) > N shift max (3)
- Hard 192h minimum requirement
- Weekly shift consistency
- Limited cross-team capacity

The fix changes 192h from a HARD to a SOFT constraint with very high penalty (100x), allowing the system to remain feasible when physical constraints make 192h impossible, while still strongly encouraging meeting the target in normal scenarios.

This surgical fix preserves all business logic while enabling robust planning even in constrained scenarios.

## Files Changed

1. **constraints.py** (lines ~3040-3064)
   - Changed minimum hours from HARD to SOFT constraint
   - Added high-penalty shortage variable
   - Added documentation explaining the change

2. **test_minimum_hours_soft_constraint.py** (NEW)
   - Comprehensive test suite for soft constraint behavior
   - Tests March 2026, February 2026, and extreme scenarios
   - Verifies constraint is actually soft

3. **MARCH_2026_INFEASIBLE_FIX.md** (THIS FILE)
   - Complete documentation of problem, analysis, and solution
   - Rationale for design decisions
   - Testing and monitoring guidance
