# Manual Shift Editing - User Guide

## Overview

The Dienstplan system now supports **manual shift editing** through the WebUI. This feature allows Admin and Disponent users to:

1. **Manually edit** individual shift assignments
2. **Lock** (fix) specific assignments to prevent automatic changes
3. **Create** new shift assignments manually
4. **Delete** shift assignments
5. **Re-run** automated planning while respecting locked assignments

---

## Features

### 1. Editing Shifts

**How to edit a shift:**

1. Navigate to the "Dienstplan" (Schedule) view
2. Click on any shift badge (e.g., "F", "S", "N") in the schedule
3. The "Schicht bearbeiten" (Edit Shift) modal will open
4. Make your changes:
   - **Employee**: Change which employee is assigned
   - **Date**: Change the date of the shift
   - **Shift Type**: Change the shift type (F/S/N/ZD)
   - **Fixed/Locked**: Check "Feste Schicht" to lock this assignment
   - **Notes**: Add optional notes about this assignment
5. Click "Speichern" (Save) to apply changes

**Permissions:**
- Only **Admin** and **Disponent** roles can edit shifts
- Regular employees (Mitarbeiter) have read-only access

---

### 2. Locking Shifts (Fixed Assignments)

**What is a locked/fixed shift?**

A locked (fixed) shift is a manually set assignment that:
- **Cannot be changed** by automatic planning
- **Will not be deleted** when re-running the shift planner
- Is **preserved** across planning runs
- Is **visually indicated** with a lock icon (🔒) and orange border

**How to lock a shift:**

**Method 1: Through the edit dialog**
1. Click on the shift to edit
2. Check the "Feste Schicht (wird nicht automatisch geändert)" checkbox
3. Click "Speichern"

**Method 2: Quick toggle** (coming soon)
- Right-click on a shift badge
- Select "Sperren" or "Entsperren"

**Visual indicator:**
- Locked shifts show a **🔒 lock icon** before the shift code
- Locked shifts have an **orange border** and glow effect
- Tooltip shows "(Fixiert)" when hovering

**Example:**
```
Regular shift:  F
Locked shift:   🔒F  (with orange border)
```

---

### 3. Creating New Shifts

**How to create a shift manually:**

1. Click the "Neue Schicht" button (when implemented) OR
2. Use the API endpoint directly:
   ```
   POST /api/shifts/assignments
   Body: {
     "employeeId": 1,
     "shiftTypeId": 1,
     "date": "2025-12-16",
     "isFixed": true,
     "notes": "Manual override"
   }
   ```

**Use cases:**
- Adding extra coverage for special events
- Filling in for absent employees
- Adjusting the schedule after employee requests

---

### 4. Deleting Shifts

**How to delete a shift:**

1. Click on the shift to edit
2. Click the red "Löschen" (Delete) button
3. Confirm the deletion

**Important:**
- You **cannot delete locked shifts** directly
- You must first unlock the shift, then delete it
- This prevents accidental deletion of important assignments

---

### 5. Automated Planning with Locked Shifts

**How locked shifts work with automatic planning:**

When you run "Schichten planen" (Plan Shifts):
1. The system **preserves all locked assignments**
2. Only **non-locked shifts** are deleted and re-planned
3. The solver **respects locked assignments** as constraints
4. New shifts are planned **around** the locked ones

**Example workflow:**

1. Initial auto-planning creates schedule
2. Admin manually adjusts 3 shifts and locks them
3. Admin runs auto-planning again
4. ✓ The 3 locked shifts remain unchanged
5. ✓ All other shifts are re-optimized
6. ✓ Schedule respects all rules with locked constraints

---

## API Endpoints

### Edit Shift Assignment
```http
PUT /api/shifts/assignments/{id}
Content-Type: application/json

{
  "employeeId": 1,
  "shiftTypeId": 1,
  "date": "2025-12-16",
  "isFixed": true,
  "notes": "Manual adjustment"
}
```

### Create Shift Assignment
```http
POST /api/shifts/assignments
Content-Type: application/json

{
  "employeeId": 1,
  "shiftTypeId": 1,
  "date": "2025-12-16",
  "isFixed": false,
  "notes": "New assignment"
}
```

### Delete Shift Assignment
```http
DELETE /api/shifts/assignments/{id}
```

### Toggle Lock Status
```http
PUT /api/shifts/assignments/{id}/toggle-fixed
```

**Response:**
```json
{
  "success": true,
  "isFixed": true
}
```

---

## Python API (Backend Integration)

The solver also supports locked assignments programmatically:

```python
from model import create_shift_planning_model
from solver import solve_shift_planning

# Define locked assignments
locked_team_shift = {
    (team_id, week_idx): shift_code
}

locked_employee_weekend = {
    (emp_id, date): is_working
}

locked_td = {
    (emp_id, week_idx): has_td
}

# Create model with locks
planning_model = create_shift_planning_model(
    employees, teams, start_date, end_date, absences,
    locked_team_shift=locked_team_shift,
    locked_employee_weekend=locked_employee_weekend,
    locked_td=locked_td
)

# Solve - locked assignments will be respected
result = solve_shift_planning(planning_model)
```

---

## Use Cases

### Use Case 1: Employee Request
**Scenario:** Employee requests a specific day off

1. Find the shift assignment for that employee/date
2. Delete the shift OR reassign to another employee
3. Lock the change to prevent auto-planning from reverting it
4. Re-run planning to optimize around this constraint

### Use Case 2: Special Event Coverage
**Scenario:** Need extra coverage for a special event

1. Manually create additional shift assignments
2. Lock them as fixed
3. These assignments will persist across all planning runs

### Use Case 3: Partial Re-Planning
**Scenario:** Schedule is mostly good, but need to adjust one week

1. Lock all shifts outside the target week
2. Run auto-planning
3. Only the unlocked week will be re-optimized
4. Unlock shifts when satisfied

### Use Case 4: Gradual Schedule Building
**Scenario:** Build schedule incrementally with manual adjustments

1. Run initial auto-planning
2. Review and manually adjust problematic assignments
3. Lock the good assignments
4. Re-run planning to improve remaining shifts
5. Repeat until satisfied

---

## Best Practices

### ✅ DO:
- Lock critical assignments that must not change
- Use notes to document why a shift was manually set
- Review locked shifts periodically to remove unnecessary locks
- Lock shifts before re-running auto-planning if you want to preserve them

### ❌ DON'T:
- Lock every shift (defeats the purpose of auto-planning)
- Forget to unlock shifts when they no longer need to be fixed
- Create manual assignments that violate constraints (solver may fail)
- Delete locked shifts without unlocking first

---

## Technical Details

### Database Schema

The `ShiftAssignments` table has these relevant fields:

- `IsManual` (BOOLEAN): Indicates if the shift was manually created
- `IsFixed` (BOOLEAN): Indicates if the shift is locked
- `ModifiedAt` (DATETIME): When the shift was last modified
- `ModifiedBy` (TEXT): Who modified the shift
- `Notes` (TEXT): Optional notes about the assignment

### Constraint Enforcement

When a shift is locked (`IsFixed = 1`):

1. **Backend:** The `_apply_locked_assignments()` function adds hard constraints:
   ```python
   model.Add(decision_variable == locked_value)
   ```

2. **Solver:** CP-SAT respects these constraints during optimization

3. **Database:** Non-fixed assignments are deleted when re-planning:
   ```sql
   DELETE FROM ShiftAssignments 
   WHERE Date >= ? AND Date <= ? AND IsFixed = 0
   ```

---

## Troubleshooting

### Problem: Can't edit shifts
**Solution:** Check your role. Only Admin and Disponent can edit.

### Problem: Shift won't delete
**Solution:** Check if it's locked. Unlock it first, then delete.

### Problem: Auto-planning overwrites manual changes
**Solution:** Lock your manual changes before re-running planning.

### Problem: Solver fails with "No solution found"
**Solution:** Your locked assignments may be conflicting with constraints. Try unlocking some assignments or adjusting them to be feasible.

### Problem: Lock icon not showing
**Solution:** Refresh the page. The lock icon (🔒) should appear on fixed shifts.

---

## Future Enhancements

Planned improvements:

- [ ] Bulk lock/unlock operations
- [ ] Right-click context menu for quick actions
- [ ] Visual drag-and-drop for shift reassignment
- [ ] Conflict detection when creating manual assignments
- [ ] History view of manual changes
- [ ] Templates for common manual adjustment patterns

---

## Summary

The manual editing feature gives you full control over the schedule:

- **Edit** any shift by clicking on it
- **Lock** shifts to preserve manual adjustments
- **Create** new assignments as needed
- **Delete** unwanted assignments
- **Re-plan** automatically while respecting locks

This provides the perfect balance between automated optimization and manual control, allowing you to leverage the power of OR-Tools while maintaining flexibility for special cases and employee requests.
