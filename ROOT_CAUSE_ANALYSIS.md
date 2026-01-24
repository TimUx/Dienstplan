# ROOT CAUSE ANALYSIS: Shift Planning Infeasibility

## Executive Summary

The shift planning system is **INFEASIBLE** for full-month planning (January/February 2026) due to a conflict between the **minimum working hours constraint** and the **team rotation constraint** when applied to teams with 5 members over a ~4.4-week period with partial weeks.

---

## Problem Configuration

### Basic Setup
- **Planning Period**: January 2026 (31 days, 4.4 weeks)
- **Start**: Thursday, January 1
- **End**: Saturday, January 31
- **Teams**: 3 teams (Alpha, Beta, Gamma)
- **Employees**: 15 total (5 per team)
- **Shift Types**: F (Frühschicht), S (Spätschicht), N (Nachtschicht)

### Shift Requirements
- **F (Early)**: 4-10 workers on weekdays, 2-5 on weekends
- **S (Late)**: 3-10 workers on weekdays, 2-5 on weekends
- **N (Night)**: 3-10 workers on weekdays, 2-5 on weekends
- **All shifts**: 8 hours per shift, 48h/week target

---

## Mathematical Analysis

### Staffing Demand
- **Weekdays**: 22 days requiring 10 workers/day (F=4, S=3, N=3)
- **Weekends**: 9 days requiring 6 workers/day (F=2, S=2, N=2)
- **Total Min Person-Days**: 274
- **Total Max Person-Days**: 795

### Employee Supply
- **Target Hours**: 48h/week × 4.4 weeks = 212.6h total
- **Days Required**: 212.6h ÷ 8h/shift = **26.6 days per employee**
- **Total Min Person-Days (All Employees)**: 15 × 26.6 = **398.6 days**

### Balance Check
✓ **Supply vs. Demand**: 398.6 employee-days > 274 required days (OK)
✓ **Max Capacity**: 398.6 < 795 maximum capacity (OK)

---

## The Core Conflict

### Team Rotation Constraint
- **Pattern**: F → N → S (3-week cycle)
- **Per Shift Per Team**: ~1.48 weeks (~10.3 days)

### The Problem: N Shift Staffing
When a team is assigned to N shift:
1. **N shift requires**: 3 workers on weekdays
2. **Team has**: 5 members
3. **Excess members**: 2 per team must work **cross-team**

### Cross-Team Bottleneck
- Each employee must work **26.6 days** in the month
- When Team A is on N shift (needs only 3 workers):
  - 2 members must find cross-team assignments
  - Available cross-team slots depend on other teams' excess capacity
  
- **The Issue**: With 3 teams rotating through the same 3 shifts over 4.4 weeks:
  - All teams face similar constraints simultaneously
  - Cross-team capacity becomes **insufficient** for all excess workers to meet their 26.6-day minimum
  - The ~1.48 rotation cycles mean some teams have incomplete rotation weeks (partial weeks at month start/end)
  - This creates **asymmetric** demand that cannot be balanced

---

## Why 1 Week Works But Full Month Doesn't

### 1 Week Planning: ✓ FEASIBLE
- **Duration**: 7 days (1 complete week)
- **Required days/employee**: 48h/week ÷ 8h = 6 days
- **Teams rotate once**: Each team gets one shift type
- **Cross-team works**: Simple to balance 2 excess workers × 3 teams over 7 days

### Full Month (31 days): ✗ INFEASIBLE
- **Duration**: 31 days (~4.4 weeks with partial weeks)
- **Required days/employee**: 26.6 days
- **Teams rotate 1.48 times**: Incomplete rotation creates uneven distribution
- **Cross-team fails**: Cannot balance excess workers over partial rotation cycles
- **Partial weeks**: Start (Thu-Sat 3 days) and End (Mon-Sat 6 days) complicate balancing

---

## Specific Constraint Violations

Based on diagnostic output, the infeasibility comes from:

1. **Minimum Working Hours Constraint** (lines 889-1013 in constraints.py)
   - Requires each employee to work minimum days to reach target hours
   - For January: 26.6 days minimum per employee

2. **Team Rotation Constraint** (team_rotation_constraints)
   - Forces F → N → S pattern
   - Each team works each shift type for ~1.48 weeks

3. **Staffing Constraints** (add_staffing_constraints)
   - Enforces min/max workers per shift per day
   - N shift: min=3, max=10

4. **The Conflict**:
   ```
   Team on N shift needs only 3 workers
   → 2 excess workers need cross-team assignments
   × 3 teams = 6 workers needing cross-team work
   
   Over ~1.5 weeks of N shift per team:
   - Each excess worker needs ~14 cross-team days (out of 26.6 total)
   - Total cross-team days needed: 6 workers × 14 days = 84 person-days
   
   Available cross-team capacity when teams are on F/S shifts:
   - Max staffing = 10 per shift
   - Own team needs = varies
   - Net capacity insufficient over partial rotation cycle
   ```

---

## Recommendations

### Option 1: Relax Minimum Hours (Quick Fix)
- Make minimum hours a **soft constraint** instead of hard
- Allow employees to work **less than 26.6 days** if needed
- **Trade-off**: Some employees may not reach full target hours

### Option 2: Increase Max Staffing Further
- Current: max=10
- **Increase to 15+** to provide more cross-team capacity
- **Trade-off**: May violate real-world operational limits

### Option 3: Adjust Team Rotation Pattern
- Instead of strict 3-week F→N→S cycles
- Allow **flexible rotation** that adapts to month length
- Ensure complete rotation cycles within planning period

### Option 4: Adjust Team Sizes
- Instead of 5 members per team
- Use **6 members** per team (18 total instead of 15)
- Provides 3 excess workers when on N shift (matches N shift max better)

### Option 5: Remove Hard Block Requirements (DONE)
- Block scheduling is now **soft** (preferences)
- This alone didn't solve the problem
- **Root cause**: minimum hours + rotation + partial weeks

---

## Test Results

| Period | Days | Result |
|--------|------|--------|
| 1 week (Mon-Sun) | 7 | ✓ FEASIBLE |
| 2 weeks (Mon-Sun) | 14 | Testing needed |
| 3 weeks (Mon-Sun) | 21 | Testing needed |
| 4 weeks (Mon-Sun) | 28 | Testing needed |
| Full January | 31 | ✗ INFEASIBLE |
| Full February | 28 | ✗ INFEASIBLE |

---

## Conclusion

**The primary constraint causing infeasibility is the combination of:**
1. **Minimum working hours requirement** (26.6 days per employee)
2. **Team rotation constraint** forcing incomplete cycles over 4.4 weeks
3. **Insufficient cross-team capacity** for excess workers during N shift assignments
4. **Partial weeks** at month boundaries creating uneven distribution

**Recommended Solution**: Make minimum working hours a **soft constraint** (preference) rather than a hard requirement, similar to how block scheduling was changed. This will allow the solver to find feasible solutions where some employees may work slightly less than the target hours, but all shifts are covered and the schedule is viable.
