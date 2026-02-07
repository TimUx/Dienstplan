# Employee Statistics Fix - System Active vs Shift Planning Active

## Problem Statement

The system was showing misleading employee statistics. It counted all employees with `IsActive = 1` as "Active Employees", but this included employees like administrators who were not assigned to any team.

From a shift planning perspective, an employee is only truly "active" if they:
1. Have `IsActive = 1` (system active)
2. Are assigned to a team (`TeamId IS NOT NULL`)

Employees without team assignments cannot participate in shift planning and should be categorized separately.

## Example of the Problem

```
Employee [1]: Admin Administrator - ACTIVE
  Personnel Number: ADMIN001
  Email: admin@fritzwinter.de
  Function: Administrator
  
--- No Team ---  ← Admin is active but not in any team
```

**Old Statistics:**
```
Employee Statistics:
  Active Employees: 1  ← Misleading - includes admin without team
  Inactive Employees: 0
  Total: 1
```

## Solution

Updated the employee statistics to distinguish between:
- **System Active**: Employees marked as active in the system
- **Shift Planning Active**: Employees that are active AND assigned to a team
- **System Inactive**: Employees marked as inactive

## Changes Made

### File: `export_system_info.py`

Updated the `_export_statistics()` method to include three separate queries:

```python
# System active: employees marked as active in the system
self.cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE IsActive = 1")
system_active_employees = self.cursor.fetchone()['count']

# Shift planning active: employees that are active AND assigned to a team
self.cursor.execute("""
    SELECT COUNT(*) as count 
    FROM Employees 
    WHERE IsActive = 1 AND TeamId IS NOT NULL
""")
shift_planning_active = self.cursor.fetchone()['count']

# Inactive employees
self.cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE IsActive = 0")
inactive_employees = self.cursor.fetchone()['count']
```

## New Statistics Output

```
Employee Statistics:
  System Active Employees: 3
  Shift Planning Active Employees (with team): 1
  System Inactive Employees: 1
  Total: 4
```

## Test Scenario

With 4 test employees:

1. **Admin Administrator** (Active, No Team)
   - Counted in: System Active
   - NOT counted in: Shift Planning Active

2. **John Doe** (Active, Team Alpha)
   - Counted in: System Active
   - Counted in: Shift Planning Active ✓

3. **Jane Smith** (Active, No Team)
   - Counted in: System Active
   - NOT counted in: Shift Planning Active

4. **Bob Johnson** (Inactive)
   - Counted in: System Inactive

**Result:**
- System Active Employees: 3 (Admin, John, Jane)
- Shift Planning Active Employees (with team): 1 (only John)
- System Inactive Employees: 1 (Bob)
- Total: 4

## Benefits

1. **Clear Distinction**: Immediately see which employees can participate in shift planning
2. **Better Planning**: Shift planners know exactly how many employees are available
3. **Accurate Reports**: Statistics reflect the reality of shift planning operations
4. **No Breaking Changes**: Only adds additional information, doesn't remove existing data

## Verification

✅ Statistics correctly distinguish system-active from shift-planning-active employees  
✅ Admin employees without teams are properly categorized  
✅ Team-assigned employees are counted in both categories  
✅ Inactive employees are correctly separated  

## Status

**COMPLETED ✅**

Date: 2026-02-07
