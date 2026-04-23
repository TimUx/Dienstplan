# Running the Tests

## One-liner from clone

```bash
./scripts/run_tests.sh -q --tb=short
```

## Setup

```bash
cd /path/to/Dienstplan
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt -r requirements-dev.txt
```

`requirements-dev.txt` includes **pytest**, **httpx** (required by Starlette’s `TestClient`), **pytest-cov**, and **pytest-timeout**.

## Quick smoke (unit only, ~10 s)

```bash
python3 -m pytest tests/unit/ -q --tb=short
```

## Default CI / local gate (no OR-Tools long runs, ~1 min)

```bash
python3 -m pytest -m "not slow" tests/ --tb=short
```

## Full suite including solver integration (~10–30 min)

```bash
python3 -m pytest tests/ --tb=short
```

## Only slow (OR-Tools) tests

```bash
python3 -m pytest -m slow tests/integration/ --tb=short
```

## Only fast E2E HTTP chains (no solver)

```bash
python3 -m pytest -m "e2e and not slow" tests/e2e/ -v --tb=short
```

## Coverage (critical packages)

```bash
python3 -m pytest -m "not slow" tests/ \
  --cov=api --cov=constraints --cov=solver --cov=model --cov=validation --cov=data_loader \
  --cov=db_init --cov-report=term-missing
```

## Single file / keyword

```bash
python3 -m pytest tests/api/test_auth.py -v
python3 -m pytest -k "dashboard" tests/ -v
```

## Markers

| Marker | Description |
|--------|-------------|
| `slow` | OR-Tools solver / long production E2E (~minutes) |
| `unit` | Pure Python, no HTTP |
| `api` | HTTP tests via `TestClient` |
| `integration` | DB, constraints import, solver pipeline |
| `e2e` | Multi-step user flows (may overlap with `api`) |

## Test data & auth

- Ephemeral SQLite per test: `tests/conftest.py` → `test_db` fixture.
- `DIENSTPLAN_INITIAL_ADMIN_EMAIL` / `DIENSTPLAN_INITIAL_ADMIN_PASSWORD` are set before `initialize_database(..., with_sample_data=True)`.
- Values are **for automated tests only**, not production defaults.

## CI (GitHub Actions)

In `.github/workflows/build-and-release.yml`, job **build-python-linux-empty** installs dev dependencies and runs the non-slow suite:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest -m "not slow" tests/ --tb=short -q
```

Re-run the same commands locally before pushing.

## Documentation

- **Feature ↔ test mapping** and the test pyramid: `TEST_STRATEGY.md`
- **Realistic dates / factories**: `tests/fixtures/realistic_data.py`, `tests/fixtures/factories.py`
