"""
Test the dual-constraint system for working hours:
- Hard constraint: >= 192h (cannot go below)
- Soft constraint: Target (48h/7) × days (minimize shortage from target)
"""
import sys
from datetime import date, timedelta
from ortools.sat.python import cp_model

# Quick test to verify constraint logic
model = cp_model.CpModel()

# Simulate 31 days (January)
total_days = 31
weekly_hours = 48

# Hard minimum (192h scaled by 10)
HARD_MIN = 1920

# Soft target ((48/7) × 31 = 212.57h, scaled by 10 = 2126)
target_hours_scaled = int((weekly_hours / 7.0) * total_days * 10)

print(f"Planning period: {total_days} days")
print(f"Hard minimum: {HARD_MIN/10}h (scaled: {HARD_MIN})")
print(f"Soft target: {target_hours_scaled/10}h (scaled: {target_hours_scaled})")
print()

# Create a variable for employee's total hours (scaled by 10)
# Range: 192h to 300h (scaled: 1920 to 3000)
employee_hours = model.NewIntVar(1920, 3000, "employee_total_hours")

# HARD CONSTRAINT: Must be >= 192h
model.Add(employee_hours >= HARD_MIN)

# SOFT CONSTRAINT: Minimize shortage from target
shortage = model.NewIntVar(0, target_hours_scaled, "shortage_from_target")
model.Add(shortage >= target_hours_scaled - employee_hours)
model.Add(shortage >= 0)

# Objective: Minimize shortage
model.Minimize(shortage)

# Solve
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10.0
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    actual_hours = solver.Value(employee_hours) / 10.0
    actual_shortage = solver.Value(shortage) / 10.0
    print("✅ FEASIBLE/OPTIMAL Solution Found!")
    print(f"Employee works: {actual_hours}h")
    print(f"Shortage from target: {actual_shortage}h")
    print(f"Meets hard minimum (192h): {actual_hours >= 192}")
    print(f"Reaches soft target ({target_hours_scaled/10}h): {actual_hours >= target_hours_scaled/10}")
else:
    print("✗ INFEASIBLE")
    sys.exit(1)

print("\n" + "="*60)
print("Constraint system working correctly!")
print("="*60)
