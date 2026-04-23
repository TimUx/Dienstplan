# Test Strategy – Dienstplan

## Goals

- **Critical behaviour** (Auth, Datenintegrität, Planungs-API, Solver-Invarianten) is covered by automated tests.
- **Unit** tests run in seconds; **API** tests use an ephemeral SQLite DB; **slow** tests run the real OR-Tools solver.
- **E2E** marks multi-step HTTP or production-pipeline tests; the fast E2E module checks UI-relevant routes without the solver.

“100 % coverage” in this project means: **all critical modules listed below have dedicated tests**, not necessarily 100 % line coverage of the entire repository (the UI layer in `wwwroot/` is tested manually or via HTTP smoke tests only).

## Test pyramid

```
             /\
            /  \   slow: solver + production DB E2E
           /----\
          / integ \  DB init, constraints export surface
         /--------\
        /   API    \  FastAPI TestClient (httpx)
       /------------\
      /     Unit     \  entities, validation, model, shared helpers
     /----------------\
```

## Feature inventory → tests

| Feature area | Routes / modules | Tests |
|--------------|------------------|--------|
| Health & metadata | `GET /api/health` | `tests/api/test_health.py` |
| CSRF & session auth | `GET /api/csrf-token`, `POST /api/auth/login`, logout, current-user | `tests/api/test_auth.py` |
| Roles | `GET /api/roles` | `tests/api/test_auth.py` |
| Employees CRUD | `/api/employees` | `tests/api/test_employees.py` |
| Teams | `GET /api/teams`, … | `tests/api/test_teams_routes.py`, `tests/api/test_employees.py` |
| Absences | `/api/absences`, absence types | `tests/api/test_absences.py` |
| Shift types & schedule | `/api/shifttypes`, `/api/shifts/schedule` | `tests/api/test_shifts.py` |
| Async planning job | `POST /api/shifts/plan`, status | `tests/api/test_shifts.py` (202 smoke) |
| Planning report read | `/api/planning/report/...` | `tests/api/test_planning_routes.py` |
| Statistics dashboard | `/api/statistics/dashboard` | `tests/api/test_statistics.py` |
| Audit logs | `/api/auditlogs`, `/api/audit-logs` | `tests/api/test_audit_routes.py` |
| Notifications | `/api/notifications` | `tests/api/test_notifications_routes.py` |
| Global & branding settings | `/api/settings/global`, branding | `tests/api/test_settings_global.py`, `tests/api/test_settings_branding.py` |
| Static Web UI | `GET /`, `/js/app.js` | `tests/api/test_static_routes.py` |
| Entities & validation | `entities.py`, `validation.py` | `tests/unit/test_entities.py`, `tests/unit/test_validation.py` |
| Data loading | `data_loader.py` | `tests/unit/test_data_loader.py` |
| CP-SAT model | `model.py` | `tests/unit/test_model.py` |
| Solver invariants | `solver.py` + `constraints/` | `tests/integration/test_solver.py`, `test_solver_2026.py`, `test_constraints_public_api.py` |
| DB schema & seed | `db_init.py` | `tests/integration/test_db_init.py` |
| Production parity pipeline | DB → loader → model → solver / HTTP job | `tests/integration/test_e2e_production.py` (`slow` + `e2e`) |
| Password & shared helpers | `api/shared.py` | `tests/unit/test_password_crypto.py`, `tests/unit/test_api_shared_helpers.py` |
| Error JSON helper | `api/error_utils.py` | `tests/unit/test_error_utils.py` |

## Critical user flows

1. **Anonymous diagnostics** – `GET /api/health`, public shift types (`tests/e2e/test_critical_user_flows.py`).
2. **Admin session** – CSRF → login → `current-user` → `GET /api/statistics/dashboard` → `GET /api/shifts/schedule` → logout (`tests/e2e/test_critical_user_flows.py`).
3. **Disponent/Admin planning** – start plan job (202) – covered in `tests/api/test_shifts.py`; full poll + DB persist in `test_e2e_production.py` (`slow`).
4. **Data stewardship** – employees/teams/absences/settings: `tests/api/test_*.py` as listed above.

## Layout

```
tests/
  conftest.py                 # app, client, admin_client, test_db
  fixtures/
    realistic_data.py         # shared calendar constants for API tests
    factories.py                # CSRF helpers, URL builders, payloads
  unit/
  api/
  integration/
  e2e/
    test_critical_user_flows.py   # fast multi-step HTTP (marker: e2e)
```

## Markers

| Marker | Meaning |
|--------|---------|
| `slow` | OR-Tools or long HTTP polling E2E |
| `unit` | No I/O |
| `api` | HTTP |
| `integration` | DB / import / solver |
| `e2e` | User-flow chains |

## Skipping slow tests (default for CI)

```bash
python3 -m pytest -m "not slow" tests/
```

## Realistic test data

- **DB**: `initialize_database(..., with_sample_data=True)` – teams, ~17 employees, standard shift types, absences.
- **Constants**: `tests/fixtures/realistic_data.py` keeps calendar ranges aligned with seeded sample rows (e.g. Feb 2025 dashboard tests).

See **`RUN_TESTS.md`** for exact CLI commands and the CI snippet.
