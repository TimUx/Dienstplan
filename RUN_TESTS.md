# Running the Tests

## Setup

```bash
cd /home/runner/work/Dienstplan/Dienstplan
pip install -r requirements-dev.txt
```

## Quick smoke test (unit tests only, ~10 s)

```bash
python -m pytest tests/unit/ -v --tb=short
```

## All fast tests (unit + API, skip solver)

```bash
python -m pytest -m "not slow" tests/ -v --tb=short
```

## All tests including solver (slow, ~10–20 min)

```bash
python -m pytest tests/ -v --tb=short
```

## Run only solver integration tests

```bash
python -m pytest -m slow tests/integration/test_solver.py -v --tb=short
```

## Run with coverage report

```bash
python -m pytest -m "not slow" tests/ --cov=. --cov-report=term-missing
```

## Run a single test file

```bash
python -m pytest tests/unit/test_entities.py -v
python -m pytest tests/api/test_health.py -v
```

## Markers

| Marker | Description |
|---|---|
| `slow` | OR-Tools solver tests (up to 30 s each) |
| `unit` | Pure Python unit tests |
| `api` | Flask HTTP endpoint tests |
| `integration` | DB / solver integration tests |

## Environment

Tests assume the working directory contains all production modules
(`entities.py`, `solver.py`, etc.). The `sys.path.insert` in each test
file handles this automatically.

## Default admin credentials (used in API tests)

- Email: `admin@fritzwinter.de`
- Password: `Admin123!`
