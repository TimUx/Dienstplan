# January 2026 Shift Planning Analysis - Quick Reference

## Problem Statement
Shift planning for January 2026 with 3 teams of 5 employees (48h/week) returns **INFEASIBLE**.

## Key Findings

### Configuration
- **15 employees** in 3 teams of 5
- **Shifts**: F (Early), S (Late), N (Night) - 8h each
- **Target**: 48h/week = 212.6h/month
- **Period**: January 2026 (31 days: 22 weekdays, 9 weekend days)

### Mathematical Requirements

| Metric | Value |
|--------|-------|
| **Days needed per employee** | **26.6 days** |
| Percentage of month | 85.7% |
| Total employee-days needed | 398.6 |
| Total employee-days available | 465 |
| Mathematical capacity | ✓ SUFFICIENT |

### Staffing Requirements

```
Average staff per day: 12.9 employees
Recommended max weekday: 15-16 employees
Recommended max weekend: 8-10 employees
Current limits (max=20) are adequate
```

## Root Cause of INFEASIBILITY

Not insufficient capacity, but **constraint conflicts**:

1. **Team rotation (F → N → S)**: Each team works ONE shift per week, all members together
2. **Consecutive work limit**: Max 6 days (need 26.6 days out of 31 = tight!)
3. **Rest time**: 11h minimum between shifts
4. **Fairness objectives**: Weekend/night distribution
5. **Combination effect**: These constraints cannot be satisfied simultaneously at 48h/week

## Solutions

### ✅ Recommended: Reduce Weekly Hours

**Change from 48h to 40h per week**

```
At 40h/week:
  Monthly hours: 177.1h (instead of 212.6h)
  Days needed: 22.1 days (instead of 26.6 days)
  Utilization: 71.3% (instead of 85.7%)
  
Result: More buffer for rest days and constraints
Status: Should become FEASIBLE
```

### ✅ Alternative: Increase Consecutive Days

**Change from 6 to 7-8 days maximum**

```
At 7 days max:
  More flexibility per week
  Fewer forced rest days
  Better target achievement
  
Note: Requires labor law review
```

### ❌ Not Recommended: Modify Team Rotation

The F → N → S rotation is likely essential for fairness and planning. Changes would destabilize the entire system.

## Implementation

### Quick Fix (entities.py):
```python
# Change weekly_working_hours from 48.0 to 40.0
ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 40.0, ...)
ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 40.0, ...)
ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 40.0, ...)
```

### Alternative Fix (constraints.py):
```python
# Increase max consecutive days
MAX_CONSECUTIVE_DAYS = 7  # instead of 6
```

## Work Distribution Example (48h/week)

```
Week 1 (7d): Team 1 on F → Employee works 6 days (max), rests 1
Week 2 (7d): Team 1 on N → Employee works 6 days, rests 1
Week 3 (7d): Team 1 on S → Employee works 6 days, rests 1
Week 4 (7d): Team 1 on F → Employee works 6 days, rests 1
Week 5 (3d): Team 1 on N → Employee works 3 days

Total: 6+6+6+6+3 = 27 days ✓ (target: 26.6)
BUT: Fairness + weekend constraints make this impossible!
```

## Weekly Schedule January 2026

| Week | Period | Days | Team 1 | Team 2 | Team 3 |
|------|--------|------|--------|--------|--------|
| 1 | 01-07 Jan | 7 | F (5) | N (5) | S (5) |
| 2 | 08-14 Jan | 7 | N (5) | S (5) | F (5) |
| 3 | 15-21 Jan | 7 | S (5) | F (5) | N (5) |
| 4 | 22-28 Jan | 7 | F (5) | N (5) | S (5) |
| 5 | 29-31 Jan | 3 | N (5) | S (5) | F (5) |

## Analysis Scripts

Three analysis scripts were created:

1. **`analyze_january_2026.py`**: Basic mathematical analysis
2. **`analyze_team_rotation_infeasibility.py`**: Detailed constraint analysis
3. **`test_january_2026_feasibility.py`**: Solver test (requires database)

All can be run with: `python <script_name>.py`

## Conclusion

✓ Mathematical capacity is sufficient (465 vs 398.6 employee-days)  
✗ Constraint combination makes 48h/week INFEASIBLE  
✅ **Solution**: Reduce to 40h/week or increase max consecutive days to 7+  
📊 **Expected result**: OPTIMAL/FEASIBLE

---

**Date**: 2026-01-21  
**Analyzed**: January 2026 (31 days)  
**Configuration**: 3 teams × 5 employees, F/S/N shifts, 48h/week
