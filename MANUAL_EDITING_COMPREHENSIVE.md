# Manual Editing and Locked Assignments Guide

## Overview

The shift planning system supports manual edits by administrators and dispatchers. Manual edits are preserved through re-solving using **locked assignments**.

## Types of Locked Assignments

### 1. Locked Team Shifts
**Purpose**: Fix a team to a specific shift in a specific week

**Use Case**: 
- Admin needs to manually adjust team rotation due to operational requirements
- Override automatic rotation pattern (F → N → S)

**Data Structure**:
```python
locked_team_shift: Dict[Tuple[int, int], str]
# Key: (team_id, week_idx)
# Value: shift_code ("F", "S", or "N")

# Example:
locked_team_shift = {
    (1, 2): "N",  # Team 1, Week 2: Force Night shift
    (2, 0): "F",  # Team 2, Week 0: Force Early shift
}
```

**How to Use**:
```python
from model import create_shift_planning_model

# Create model with locked team shifts
planning_model = create_shift_planning_model(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    locked_team_shift=locked_team_shift
)
```

### 2. Locked Employee Weekend Work
**Purpose**: Fix whether an employee works on a specific weekend day

**Use Case**:
- Admin wants to ensure employee works (or doesn't work) on specific Saturday/Sunday
- Balance weekend workload manually

**Data Structure**:
```python
locked_employee_weekend: Dict[Tuple[int, date], bool]
# Key: (employee_id, date)
# Value: True = must work, False = must not work

# Example:
from datetime import date
locked_employee_weekend = {
    (5, date(2025, 1, 11)): True,   # Employee 5 MUST work on Jan 11 (Sat)
    (7, date(2025, 1, 12)): False,  # Employee 7 MUST NOT work on Jan 12 (Sun)
}
```

**How to Use**:
```python
planning_model = create_shift_planning_model(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    locked_employee_weekend=locked_employee_weekend
)
```

### 3. Locked TD (Day Duty) Assignments
**Purpose**: Fix TD assignment to a specific employee in a specific week

**Use Case**:
- Admin wants specific TD-qualified employee to handle TD this week
- Override automatic TD distribution

**Data Structure**:
```python
locked_td: Dict[Tuple[int, int], bool]
# Key: (employee_id, week_idx)
# Value: True = must have TD, False = must not have TD

# Example:
locked_td = {
    (16, 1): True,   # Employee 16 MUST have TD in week 1
    (16, 2): False,  # Employee 16 MUST NOT have TD in week 2
}
```

**How to Use**:
```python
planning_model = create_shift_planning_model(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    locked_td=locked_td
)
```

### 4. Locked Absences (NEW)
**Purpose**: Fix absence code for a specific employee on a specific date

**Use Case**:
- Absences entered AFTER scheduling
- Manual correction of absence records
- Ensure absences persist through re-solving

**Data Structure**:
```python
locked_absence: Dict[Tuple[int, date], str]
# Key: (employee_id, date)
# Value: absence_code ("U", "AU", or "L")

# Example:
from datetime import date
locked_absence = {
    (3, date(2025, 1, 15)): "U",   # Employee 3: Vacation on Jan 15
    (7, date(2025, 1, 20)): "AU",  # Employee 7: Sick leave on Jan 20
}
```

**How to Use**:
```python
planning_model = create_shift_planning_model(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    locked_absence=locked_absence
)
```

**IMPORTANT**: Absences in the `absences` list are ALWAYS locked by default (via `is_locked=True` flag).

## Complete Example: Re-solving with Manual Edits

```python
from datetime import date, timedelta
from model import create_shift_planning_model
from solver import solve_shift_planning
from data_loader import load_from_database

# 1. Load data
employees, teams, absences = load_from_database("dienstplan.db")

# 2. Define planning period
start_date = date(2025, 1, 1)
end_date = date(2025, 1, 31)

# 3. Define manual edits (locked assignments)
locked_team_shift = {
    (1, 0): "F",  # Team 1, Week 0: Early shift
}

locked_employee_weekend = {
    (5, date(2025, 1, 11)): True,   # Employee 5 works on Jan 11
    (5, date(2025, 1, 12)): False,  # Employee 5 does NOT work on Jan 12
}

locked_td = {
    (16, 1): True,  # Employee 16 has TD in week 1
}

# Locked absences (optional - absences list already provides locking)
locked_absence = {
    (3, date(2025, 1, 15)): "U",  # Employee 3: vacation
}

# 4. Create model with all locked assignments
planning_model = create_shift_planning_model(
    employees=employees,
    teams=teams,
    start_date=start_date,
    end_date=end_date,
    absences=absences,
    locked_team_shift=locked_team_shift,
    locked_employee_weekend=locked_employee_weekend,
    locked_td=locked_td,
    locked_absence=locked_absence
)

# 5. Solve
result = solve_shift_planning(planning_model, time_limit_seconds=300)

if result:
    assignments, special_functions, complete_schedule = result
    print(f"✓ Solution found with {len(assignments)} assignments")
    print("  Manual edits were preserved!")
else:
    print("✗ No solution found - check if manual edits create conflicts")
```

## Workflow: Post-Scheduling Absence Handling

When an absence is entered AFTER the schedule is already generated:

### Step 1: Detect the Absence
```python
from entities import Absence, AbsenceType

# New absence entered by admin/dispatcher
new_absence = Absence(
    id=101,
    employee_id=5,
    absence_type=AbsenceType.U,  # Vacation
    start_date=date(2025, 1, 15),
    end_date=date(2025, 1, 17),
    notes="Last-minute vacation"
)
```

### Step 2: Attempt Springer Replacement
```python
from springer_replacement import (
    handle_post_scheduling_absence,
    get_affected_shifts_for_absence
)

# Get the affected employee and team
employee = next(e for e in employees if e.id == new_absence.employee_id)
team = next((t for t in teams if t.id == employee.team_id), None)

# Get affected shifts
affected_shifts = get_affected_shifts_for_absence(
    employee, new_absence, existing_assignments
)

# Attempt springer replacement
new_assignments, dates_without_replacement = handle_post_scheduling_absence(
    absence=new_absence,
    employee=employee,
    team=team,
    schedule_month="January 2025",
    affected_dates=list(affected_shifts.keys()),
    affected_shifts=affected_shifts,
    springers=[e for e in employees if e.is_springer],
    existing_assignments=existing_assignments,
    all_absences=absences + [new_absence]
)

print(f"✓ Created {len(new_assignments)} springer assignments")
print(f"⚠ {len(dates_without_replacement)} dates without replacement")
```

### Step 3: Update Database and Re-solve (if needed)
```python
# Add new absence to database
# Add new springer assignments to database
# If no replacement possible, re-solve with locked assignments

if dates_without_replacement:
    # Re-solve with absence locked
    all_absences = absences + [new_absence]
    
    planning_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=all_absences,  # Absences are automatically locked
        locked_team_shift=existing_locked_team_shift,
        locked_employee_weekend=existing_locked_employee_weekend,
        locked_td=existing_locked_td
    )
    
    result = solve_shift_planning(planning_model)
```

## Absence Priority Rules

**CRITICAL**: Absences ALWAYS take highest priority:

1. **Absence** (U, AU, L) - HIGHEST PRIORITY
2. **TD** (Day Duty) - Second priority
3. **Regular Shifts** (F, S, N) - Third priority
4. **OFF** (No work) - Default

**Example**:
- If employee has shift assignment AND absence on same day → Show absence code
- If employee has TD AND absence on same day → Show absence code
- Absences ALWAYS override everything else

## Notification Triggers

When manual edits or absences affect scheduling:

### 1. Absence After Scheduling
**Triggered**: When absence entered after schedule generated
**Recipients**: All Admins, All Dispatchers
**Payload**: Employee, absence details, affected dates

### 2. Springer Assigned
**Triggered**: When springer automatically assigned to replace absent employee
**Recipients**: The springer, All Admins, All Dispatchers
**Payload**: Springer details, original employee, shift details

### 3. No Replacement Available
**Triggered**: When no springer can replace absent employee
**Recipients**: All Admins, All Dispatchers
**Payload**: Employee, shift details, reason no replacement, understaffing impact

### 4. Locked Assignment Conflict
**Triggered**: When locked assignment prevents optimization
**Recipients**: All Admins, All Dispatchers
**Payload**: Locked assignment details, conflict description

## Database Schema for Manual Edits

To persist manual edits, extend the database:

```sql
-- Store locked team shifts
CREATE TABLE IF NOT EXISTS LockedTeamShifts (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TeamId INTEGER NOT NULL,
    WeekStartDate TEXT NOT NULL,
    ShiftCode TEXT NOT NULL,
    LockedBy TEXT,
    LockedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Reason TEXT,
    FOREIGN KEY (TeamId) REFERENCES Teams(Id)
);

-- Store locked employee weekend work
CREATE TABLE IF NOT EXISTS LockedWeekendWork (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    EmployeeId INTEGER NOT NULL,
    Date TEXT NOT NULL,
    MustWork INTEGER NOT NULL,  -- 1=must work, 0=must not work
    LockedBy TEXT,
    LockedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Reason TEXT,
    FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
);

-- Store locked TD assignments
CREATE TABLE IF NOT EXISTS LockedTdAssignments (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    EmployeeId INTEGER NOT NULL,
    WeekStartDate TEXT NOT NULL,
    HasTd INTEGER NOT NULL,  -- 1=must have TD, 0=must not have TD
    LockedBy TEXT,
    LockedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Reason TEXT,
    FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
);
```

## Best Practices

1. **Use Sparingly**: Locked assignments reduce solver flexibility
2. **Document Reasons**: Always add notes explaining why assignment was locked
3. **Check Feasibility**: Verify locked assignments don't create impossible constraints
4. **Review Regularly**: Remove locks when no longer needed
5. **Test Re-solving**: Always test that schedule can be re-solved with locks
6. **Absence Priority**: Remember absences ALWAYS override other assignments

## Troubleshooting

### Problem: Solver finds no solution after adding locks

**Solution**: Check if locked assignments create conflicts:
- Verify rest time constraints (11 hours between shifts)
- Check maximum consecutive shifts (6 days)
- Ensure minimum staffing can be met
- Review locked weekend work vs. team shifts

### Problem: Absences not showing in schedule

**Solution**: 
- Verify absence is in `absences` list
- Check `is_locked=True` flag is set
- Confirm absence dates overlap with planning period
- Review `complete_schedule` extraction logic

### Problem: Manual edit lost after re-solving

**Solution**:
- Ensure locked assignment dictionary is passed to model
- Verify lock is applied in `_apply_locked_assignments()`
- Check database persistence of locked assignments
- Review that existing locks are loaded before re-solving

## API Integration

For web interface, create endpoints to manage locked assignments:

```python
# Example Flask endpoints

@app.route('/api/locked-assignments/team-shift', methods=['POST'])
@require_role(['Admin', 'Disponent'])
def lock_team_shift():
    """Lock a team to a specific shift in a week"""
    data = request.json
    # Save to database
    # Return success

@app.route('/api/locked-assignments/weekend', methods=['POST'])
@require_role(['Admin', 'Disponent'])
def lock_weekend_work():
    """Lock employee weekend work"""
    data = request.json
    # Save to database
    # Return success

# Similar endpoints for TD and absences
```
