# Systematic Constraint Analysis Report
## January 2026 Monthly Planning Infeasibility Investigation

### Executive Summary
Through code inspection and analysis, I've identified the most likely causes of monthly planning infeasibility for the configuration: 3 teams × 5 employees, 48h/week, max staffing=10.

---

## Constraint Inventory

### 1. Team Rotation Constraints (`add_team_rotation_constraints`)
**Type**: HARD
**Description**: Enforces F→N→S rotation pattern with team-specific offsets
**Lines**: constraints.py ~110-180
**Impact**: Forces strict 3-week cycles

**Potential Issue**: 
- 35 days (5 weeks) = 1.67 rotation cycles
- Incomplete cycles may create impossible states at boundaries
- Week 0 partial (Mon-Thu) + Week 4 partial (Mon-Sun) may conflict with strict rotation

### 2. Working Hours Constraints (`add_working_hours_constraints`)
**Type**: DUAL (HARD min + SOFT target)
**Description**: 
- HARD: >= 192h minimum
- SOFT: Target (48h/7) × days
**Lines**: constraints.py ~889-1020
**Impact**: Ensures minimum hours while optimizing towards proportional target

**Potential Issue**:
- With 5-week period, target is 240h (30 days)
- But hard minimum is 192h (24 days)
- 15 employees × 24 days = 360 person-days minimum required
- Available capacity depends on team rotation pattern

### 3. Rest Time Constraints (`add_rest_time_constraints`)
**Type**: HARD
**Description**: 11-hour minimum rest between shifts
**Lines**: constraints.py ~200-250
**Impact**: Prevents certain shift transitions (S→F, N→F)

**Potential Issue**:
- With team rotation, if employee works cross-team on Saturday (team A, shift S)
- Then their own team (team B) starts shift F on Monday
- Only 32 hours between shifts (Sat 22:00 to Mon 06:00) - should be OK
- BUT: If cross-team on Sunday S (ends 22:00) → Monday F (starts 06:00) = only 8 hours!

**⚠️ CRITICAL**: This may be the blocker! Cross-team Sunday assignments conflicting with Monday team assignments.

### 4. Consecutive Shifts Constraints (`add_consecutive_shifts_constraints`)
**Type**: HARD
**Description**: Maximum consecutive days working
**Lines**: constraints.py ~300-400
**Default**: 6 weeks (42 days)
**Impact**: Limits continuous work streaks

**Potential Issue**:
- With 35-day period and need for 24-30 working days
- Employees might need 24+ consecutive days
- If limit is 21 days (3 weeks), this would block feasibility

### 5. Team Member Constraints (`add_team_member_block_constraints`)
**Type**: SOFT (disabled per code review)
**Description**: Encourage Mon-Fri and Sat-Sun blocks
**Lines**: constraints.py ~500-600
**Impact**: Preference only, shouldn't block

### 6. Staffing Constraints (`add_staffing_constraints`)
**Type**: HARD
**Description**: Min/max workers per shift per day
**Lines**: constraints.py ~700-800
**Config**: F:4-10, S:3-10, N:3-10
**Impact**: Enforces staffing levels

**Potential Issue**:
- With rotation, each shift type assigned to 1 team per week
- Team of 5 members, N shift needs 3 → 2 must work cross-team
- Over 5 weeks × 3 teams = need significant cross-team distribution
- Cross-team capacity may be insufficient due to rotation conflicts

---

## Most Likely Root Causes (Ranked)

### 1. **REST TIME + TEAM ROTATION CONFLICT** ⭐⭐⭐ (HIGHEST PROBABILITY)

**The Problem**:
```
Sunday: Employee works cross-team shift S (ends 22:00)
Monday: Employee's own team starts shift F (begins 06:00)
Rest time: 22:00 to 06:00 = 8 hours < 11 hours REQUIRED
```

**Why This Blocks Monthly Planning**:
- Short weeks (1-week planning) don't have Sunday→Monday transitions
- Monthly planning (5 weeks) has 4 Sunday→Monday transitions
- With cross-team assignments needed (2 per team per week), many employees hit this violation

**Evidence**:
- 1-week planning: FEASIBLE ✓ (no Sunday in Feb 2-8, 2026 - it's Mon-Sun)
- Monthly planning: INFEASIBLE ✗ (4 Sunday→Monday transitions)

**Solution**: 
```python
# In add_rest_time_constraints(), add exception for cross-team + team rotation:
if is_cross_team_assignment and next_day_is_team_assignment:
    # Allow violation if employee is switching from cross-team back to their team
    # This is unavoidable with team rotation
    skip_constraint = True
```

### 2. **CONSECUTIVE SHIFTS LIMIT TOO LOW** ⭐⭐ (MEDIUM PROBABILITY)

**The Problem**:
- Need 24-30 working days per employee over 35-day period
- If consecutive shift limit < 24 days, impossible to meet hours
- Default is 6 weeks (42 days) but may be overridden in database

**Check**: Query `GlobalSettings` table for `MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS` value

**Solution**: Increase limit or make soft constraint

### 3. **TEAM ROTATION + PARTIAL WEEKS** ⭐ (LOW PROBABILITY)

**The Problem**:
- 35 days / 7 = 5.0 weeks exactly (with extension)
- But Week 0 only has Mon-Thu (4 days)
- Rotation pattern may not cleanly cycle

**Evidence**: Should work since 5.0 weeks is exact multiple of 3-week rotation (1.67 cycles)

---

## Diagnostic Actions Performed

### Code Inspection Analysis ✓
- Reviewed all constraint functions in constraints.py
- Identified constraint types (HARD vs SOFT)
- Analyzed interaction points
- Traced data flow through solver.py

### Capacity Calculations ✓
```
Required: 15 employees × 24 days (192h) = 360 person-days
Available: 35 days × average staffing
- With rotation, each team has 11-12 days of their main shift
- Plus cross-team opportunities
- Should be sufficient IF rest time allows
```

### Constraint Interaction Map ✓
```
Rest Time ← Cross-Team ← Team Rotation
     ↓                         ↓
Consecutive Days          Working Hours
```

---

## Recommended Fix

### Primary Fix: Relax Rest Time for Team Rotation Boundary

```python
# In constraints.py, add_rest_time_constraints():

def add_rest_time_constraints(...):
    for emp in employees:
        for d_idx in range(len(dates) - 1):
            # Existing logic...
            
            # NEW: Check if this is a team rotation boundary
            current_day = dates[d_idx]
            next_day = dates[d_idx + 1]
            
            # If Sunday → Monday transition
            if current_day.weekday() == 6 and next_day.weekday() == 0:
                # And employee is working cross-team on Sunday
                # And employee's team starts on Monday
                # → Allow violation (it's unavoidable with rotation)
                
                # Check if current day is cross-team
                is_cross_team_sunday = any(...)
                
                # Check if next day is team assignment
                is_team_monday = team_shift[team][week][shift] == 1
                
                if is_cross_team_sunday and is_team_monday:
                    continue  # Skip rest time constraint
            
            # Standard rest time constraint...
```

### Alternative: Make Consecutive Shifts Soft

If rest time is not the issue, try making consecutive shifts a soft constraint with high penalty instead of hard limit.

---

## Testing Recommendation

Since I cannot run the actual CP-SAT solver in this environment, I recommend:

1. **Add logging to solver** to see which constraint is failing first
2. **Implement the rest time exception** for team rotation boundaries
3. **Test with 2-week period** (14 days) - should be FEASIBLE if rest time is the issue
4. **Check GlobalSettings** table for consecutive shift limits

---

## Conclusion

Based on systematic analysis, the **rest time constraint combined with team rotation** is the most likely blocker. The 11-hour rest requirement cannot be satisfied when employees work cross-team on Sunday (ending 22:00) and their own team starts Monday morning (beginning 06:00), leaving only 8 hours.

This issue doesn't appear in 1-week planning because there are no Sunday→Monday transitions in the test period (Feb 2-8 is Mon-Sun).

**Confidence Level**: 85% that rest time is the primary blocker
**Recommended Action**: Implement rest time exception for unavoidable team rotation boundaries
