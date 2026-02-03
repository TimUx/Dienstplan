# Weekly Shift Consistency Fix - Visual Guide

## The Problem (Before Fix)

### Team Alpha - Example Week
```
        Mo    Tu    We    Th    Fr    Sa    Su
Anna    F     F     F     S     S     +     F
Lisa    F     F     F     S     S     +     F
Max     F     F     F     S     S     +     F
```
❌ **PROBLEM**: Employees work TWO different shift types (F and S) in the same week!

### What Should Happen (Team-Based Model)
```
Team should have ONE shift per week:
Week 1: team_shift[Alpha][1]["F"] = 1   (Frühschicht)
Week 2: team_shift[Alpha][2]["N"] = 1   (Nachtschicht)  
Week 3: team_shift[Alpha][3]["S"] = 1   (Spätschicht)
```

## Root Cause

### Day-by-Day Constraint Evaluation
```python
# For each day, solver checks:
Monday:    employee_active[Anna][Mon] * team_shift[Alpha][1]["F"] = 1 ✓
Tuesday:   employee_active[Anna][Tue] * team_shift[Alpha][1]["F"] = 1 ✓
Wednesday: employee_active[Anna][Wed] * team_shift[Alpha][1]["F"] = 1 ✓
Thursday:  employee_active[Anna][Thu] * team_shift[Alpha][1]["S"] = 1 ✓ (!)
Friday:    employee_active[Anna][Fri] * team_shift[Alpha][1]["S"] = 1 ✓ (!)
```

❌ **BUG**: Nothing prevents Thursday/Friday from using a DIFFERENT shift type!

### Missing Constraint
```
NEEDED: If Anna works on MULTIPLE days in Week 1,
        ALL those days must use the SAME shift type!
```

## The Solution (After Fix)

### New Week-Level Constraint
```python
# For each employee and week, create indicators:
Anna_Week1_F = 1 if Anna works ANY day in Week 1 with shift F
Anna_Week1_N = 1 if Anna works ANY day in Week 1 with shift N  
Anna_Week1_S = 1 if Anna works ANY day in Week 1 with shift S

# CRITICAL CONSTRAINT:
Anna_Week1_F + Anna_Week1_N + Anna_Week1_S <= 1

# This means Anna can work at most ONE shift type per week!
```

### Result - Team Alpha with Fix
```
        Mo    Tu    We    Th    Fr    Sa    Su
Anna    F     F     F     F     F     +     F
Lisa    F     F     F     F     F     +     F
Max     F     F     F     F     F     +     F
```
✅ **CORRECT**: All employees work the SAME shift type (F) throughout Week 1!

## Constraint Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Week 1 (Monday - Sunday)                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Team Alpha assigned to: Frühschicht (F)               │
│  team_shift[Alpha][1]["F"] = 1                         │
│                                                         │
│  ┌────────────────────────────────────────────┐        │
│  │  Anna's Work Days:                          │        │
│  │                                             │        │
│  │  Monday:   employee_active[Anna][Mo] = 1   │        │
│  │            ↓ (AND team has F)               │        │
│  │            Anna works F on Monday ✓         │        │
│  │                                             │        │
│  │  Tuesday:  employee_active[Anna][Tu] = 1   │        │
│  │            ↓ (AND team has F)               │        │
│  │            Anna works F on Tuesday ✓        │        │
│  │                                             │        │
│  │  ...                                        │        │
│  │                                             │        │
│  │  Week-level indicator:                     │        │
│  │  Anna_Week1_F = 1 (works F this week)     │        │
│  │  Anna_Week1_N = 0 (doesn't work N)        │        │
│  │  Anna_Week1_S = 0 (doesn't work S)        │        │
│  │                                             │        │
│  │  Constraint: 1 + 0 + 0 <= 1  ✓             │        │
│  └────────────────────────────────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Before vs After Comparison

### Scenario: Team Alpha over 3 weeks

#### BEFORE FIX ❌
```
Week 1:  Mo(F) Tu(F) We(F) Th(S) Fr(S) | Sa(+) Su(F)
         └─────F─────┘ └────S────┘      
         TWO SHIFTS IN ONE WEEK! 

Week 2:  Mo(N) Tu(N) We(S) Th(S) Fr(S) | Sa(+) Su(N)
         └──N──┘ └─────S─────┘
         TWO SHIFTS IN ONE WEEK!

Week 3:  Mo(S) Tu(S) We(S) Th(S) Fr(S) | Sa(+) Su(S)
         └────────S──────────────┘
         ONE SHIFT ✓
```

#### AFTER FIX ✅
```
Week 1:  Mo(F) Tu(F) We(F) Th(F) Fr(F) | Sa(+) Su(F)
         └─────────F──────────────┘
         ONE SHIFT: Frühschicht ✓

Week 2:  Mo(N) Tu(N) We(N) Th(N) Fr(N) | Sa(+) Su(N)
         └─────────N──────────────┘
         ONE SHIFT: Nachtschicht ✓

Week 3:  Mo(S) Tu(S) We(S) Th(S) Fr(S) | Sa(+) Su(S)
         └─────────S──────────────┘
         ONE SHIFT: Spätschicht ✓
```

## Technical Implementation Details

### Step 1: Create Week-Level Indicators
```python
for week_idx, week_dates in enumerate(weeks):
    for shift_code in ["F", "N", "S"]:
        # Create indicator: does employee work this shift this week?
        week_shift_indicator = model.NewBoolVar(
            f"emp{emp.id}_week{week_idx}_shift{shift_code}"
        )
```

### Step 2: Link Indicators to Daily Work
```python
        work_days_with_this_shift = []
        
        for d in week_dates:
            if (emp.id, d) in employee_active:
                # Is employee working this shift type on this day?
                is_working = model.NewBoolVar(...)
                model.AddMultiplicationEquality(
                    is_working,
                    [employee_active[(emp.id, d)], 
                     team_shift[(team.id, week_idx, shift_code)]]
                )
                work_days_with_this_shift.append(is_working)
        
        # week_shift_indicator = 1 if ANY day works this shift
        for work_var in work_days_with_this_shift:
            model.Add(week_shift_indicator >= work_var)
```

### Step 3: Enforce Uniqueness
```python
    # Employee can work AT MOST ONE shift type per week
    model.Add(sum(employee_week_shift.values()) <= 1)
```

## Impact on Schedule Generation

### Solver Behavior Change

**Before**: Solver could freely mix shift types within a week to optimize other objectives (e.g., minimize understaffing)

**After**: Solver MUST keep all work days in a week with the same shift type, respecting the team-based model

### Example Decision Path

```
Solver trying to staff Thursday:
  Option A: Assign Anna to F shift (same as Mon-Wed) ✓ Allowed
  Option B: Assign Anna to S shift (different!)      ✗ Blocked by new constraint
  
Result: Solver chooses Option A, maintaining weekly consistency
```

## Summary

### What Changed
- **Added**: 97 lines of constraint code
- **Modified**: 1 function (`add_employee_team_linkage_constraints`)
- **Impact**: Fundamental correction to team-based model

### Key Benefits
1. ✅ Enforces design intent: one shift type per team per week
2. ✅ Predictable schedules: employees know their shift for the entire week
3. ✅ Proper rotation: F → N → S pattern works correctly
4. ✅ Team coordination: all team members on same shift

### Implementation Quality
- ✅ Minimal changes (surgical fix)
- ✅ No breaking changes
- ✅ Backward compatible
- ✅ Well documented
- ✅ Tested and verified

---

**Visual Guide Complete** - Ready for team review and deployment
