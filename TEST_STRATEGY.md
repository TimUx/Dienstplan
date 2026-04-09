# Test Strategy – Dienstplan

## Overview

This document describes the testing strategy for the Dienstplan shift-planning system.

## Test Pyramid

```
             /\
            /  \  Integration / Solver
           /----\
          / API  \  API Tests (Flask test client)
         /--------\
        /   Unit   \  Entity, Validation, DataLoader, Model
       /------------\
```

## Test Categories

| Category | Location | Marker | Description |
|---|---|---|---|
| Unit | `tests/unit/` | `unit` | Pure Python logic, no I/O |
| Integration | `tests/integration/` | `integration` | DB init, full solver runs |
| API | `tests/api/` | `api` | Flask HTTP endpoints |
| Slow | solver tests | `slow` | OR-Tools solver (up to 30 s each) |

## File Structure

```
tests/
  conftest.py              # Shared fixtures (app, client, admin_client, test_db)
  fixtures/
    factories.py           # Factory helpers for test data objects
  unit/
    test_entities.py       # Employee, ShiftType, Absence, STANDARD_SHIFT_TYPES
    test_validation.py     # All validate_* functions
    test_data_loader.py    # generate_sample_data()
    test_model.py          # ShiftPlanningModel creation / date extension
  integration/
    test_solver.py         # solve_shift_planning() – 15+ scenarios
    test_db_init.py        # initialize_database() – schema & idempotency
  api/
    test_auth.py           # /api/csrf-token, /api/auth/login, logout, me
    test_employees.py      # /api/employees CRUD, /api/teams
    test_absences.py       # /api/absences, /api/absencetypes
    test_shifts.py         # /api/shifttypes, /api/shifts/schedule, /api/shifts/plan
    test_health.py         # /api/health
```

## Critical Invariants (always checked in solver tests)

1. **No duplicate shifts per day** – each `(employee_id, date)` pair appears at most once in `assignments`.
2. **No work during absences** – no assignment overlaps with any recorded absence.
3. **Valid shift codes** – every assignment references a shift type present in `STANDARD_SHIFT_TYPES`.
4. **PlanningReport.status** is one of `OPTIMAL | FEASIBLE | FALLBACK_L1 | FALLBACK_L2 | EMERGENCY`.

## Key Test Data

- Admin credentials: `admin@fritzwinter.de` / `Admin123!`
- Default DB seeded by `initialize_database(db_path, with_sample_data=True)`
- Sample data: 17 employees, 3 teams, sample absences (U / AU / L)
- All solver tests use `STANDARD_SHIFT_TYPES` as `shift_types`

## Skipping Slow Tests

```bash
# Skip solver tests (fast CI)
pytest -m "not slow" tests/

# Run only solver tests
pytest -m slow tests/integration/test_solver.py
```
