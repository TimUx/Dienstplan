# Fix Summary: Absence Compensation with Springers

## Problem Statement

When planning shifts for January 2026, the system returned `INFEASIBLE` error when employees were absent (AU - sick leave, U - vacation). The error message showed:

```
Unsat after presolving constraint #536: linear { vars: 994 vars: 995 vars: 996 coeffs: 1 coeffs: 1 coeffs: 1 domain: 4 domain: 5 }
```

This indicated a staffing constraint requiring 4-5 people but only 3 variables available. The user mentioned that one employee was AU (sick) and another on vacation (U), which should be compensated by springers or team members.

## Root Cause

The staffing constraints in `constraints.py` explicitly excluded springers from being counted toward staffing requirements:

```python
# Line 301-302 (OLD)
if emp.team_id != team.id or emp.is_springer:
    continue  # Only count regular team members
```

This meant that even though springers exist in teams and can work shifts, they weren't counted when checking if staffing requirements (min 4 for F shift) were met. When regular team members were absent, the remaining team members couldn't meet minimum staffing, resulting in INFEASIBLE.

## Solution

**Modified `constraints.py` - `add_staffing_constraints()` function**:

Removed the springer exclusion from weekday staffing constraint counting:

```python
# Line 301-302 (NEW)
if emp.team_id != team.id:
    continue  # Only count team members (springers ARE team members)
```

This simple change allows springers to be counted as regular team members for staffing purposes, enabling them to compensate when others are absent.

## Changes Made

### 1. Code Changes

**File: `constraints.py`**
- Line ~301: Removed `or emp.is_springer` from team member check
- Line ~294: Updated comment to clarify springers ARE team members
- Line ~263: Added documentation explaining weekend springer exclusion is by design

### 2. Test Coverage

**New file: `test_absence_compensation.py`**
- Test 1: January 2026 scenario (from problem statement)
  - 31-day period with 2 absences (1 AU, 1 U)
  - Verifies springers compensate for absent employees
- Test 2: Multiple simultaneous absences
  - One absence per team (3 total)
  - Stress-tests springer compensation across all teams

## Test Results

### Existing Tests (test_shift_model.py)
All 6 tests continue to pass:
```
✅ PASS: Weekday Consistency
✅ PASS: Weekend Team Consistency
✅ PASS: Team Rotation
✅ PASS: Ferienjobber Exclusion
✅ PASS: TD Assignment
✅ PASS: Staffing Requirements
Total: 6/6 tests passed
```

### New Absence Compensation Tests
```
✅ PASS: January 2026 with absences
   - Period: Dec 31, 2025 - Jan 30, 2026 (31 days)
   - Absences: 2 (1 AU, 1 U)
   - Solution: OPTIMAL in 10.38 seconds
   - Assignments: 281 total
   - Springer days: 45 (15-16 per springer)

✅ PASS: Single absence per team
   - Period: Jan 5-18, 2026 (14 days)
   - Absences: 3 (1 per team: AU, U, L)
   - Solution: OPTIMAL in 3.26 seconds
   - Springer days: 20

Total: 2/2 tests passed
```

### Quality Checks
- ✅ Code Review: 1 comment addressed (weekend consistency documented)
- ✅ Security Scan (CodeQL): No alerts

## Technical Details

### Team Structure
Each team has 5 members:
- 4 regular employees
- 1 springer (backup worker)

Before the fix:
- Regular member absent → Only 3 regular members available
- Springer available but NOT counted → INFEASIBLE (needs min 4)

After the fix:
- Regular member absent → 3 regular + 1 springer = 4 available
- Springer IS counted → FEASIBLE (meets min 4)

### Weekend Handling
Weekends still exclude springers because:
1. Springers don't have weekend variables (model.py line 198)
2. Weekend staffing is lower (2-3 vs 4-5)
3. Regular team members can usually meet weekend requirements

This is an acceptable design limitation and is now properly documented.

### Springer Constraint
The springer constraint (at least 1 available per day) remains active, ensuring not all springers are assigned simultaneously.

## Impact

### Before Fix
```
Planning January 2026 with absences:
❌ INFEASIBLE - No solution found
```

### After Fix
```
Planning January 2026 with absences:
✅ OPTIMAL solution found in 10.38 seconds
   282 assignments generated
   Springers compensate for absences
```

## Recommendations

1. **Monitor springer workload**: With this fix, springers may work more frequently. Consider fairness objectives if needed.

2. **Cross-team springer support**: Currently, springers only work within their own team. For extreme scenarios (multiple absences in one team), consider allowing springers to work in other teams.

3. **Weekend springer support**: If weekend coverage becomes an issue, extend the model to create weekend variables for springers.

4. **Absence planning**: The system now handles realistic absence levels (1-2 per period). For higher absence rates, additional staffing may be needed.

## Conclusion

The fix successfully resolves the INFEASIBLE error when employees are absent. Springers now properly compensate for absent team members by being counted in staffing constraints. The solution:

- ✅ Fixes the January 2026 planning issue
- ✅ Maintains all existing test compliance
- ✅ Adds comprehensive test coverage for absence scenarios
- ✅ Is minimal and surgically precise (3 lines changed)
- ✅ Has no security issues
- ✅ Is well-documented

The shift planning system can now handle realistic absence scenarios as intended.
