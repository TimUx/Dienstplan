"""Shared fixtures for the Dienstplan test suite."""

import gc
import os
import sys
import time

import pytest


from datetime import date
from entities import (
    Employee, Team, Absence, AbsenceType, ShiftAssignment,
    STANDARD_SHIFT_TYPES,
)
from data_loader import generate_sample_data

TEST_ADMIN_EMAIL = "admin@fritzwinter.de"
TEST_ADMIN_PASSWORD = "Admin123!"


@pytest.fixture
def sample_employees_teams_absences():
    return generate_sample_data()


@pytest.fixture
def standard_shift_types():
    return list(STANDARD_SHIFT_TYPES)


@pytest.fixture
def test_db(tmp_path):
    """Isolated SQLite database for each test."""
    db_path = str(tmp_path / "test.db")
    from db_init import initialize_database
    os.environ["DIENSTPLAN_INITIAL_ADMIN_EMAIL"] = TEST_ADMIN_EMAIL
    os.environ["DIENSTPLAN_INITIAL_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
    initialize_database(db_path, with_sample_data=True)
    yield db_path
    if not os.path.exists(db_path):
        return
    # Windows keeps SQLite files locked until connections are GC'd; release then retry remove.
    gc.collect()
    attempts = 12 if sys.platform == 'win32' else 1
    last_err = None
    for i in range(attempts):
        try:
            os.remove(db_path)
            return
        except PermissionError as e:
            last_err = e
            gc.collect()
            if i + 1 < attempts:
                time.sleep(0.05)
    raise last_err


@pytest.fixture
def app(test_db):
    """FastAPI test application."""
    from web_api import create_app
    return create_app(test_db)


@pytest.fixture
def client(app):
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_client(client):
    """Authenticated admin test client with CSRF token."""
    resp = client.get('/api/csrf-token')
    csrf = resp.json()['token']
    client.post(
        '/api/auth/login',
        json={'email': TEST_ADMIN_EMAIL, 'password': TEST_ADMIN_PASSWORD},
        headers={'X-CSRF-Token': csrf},
    )
    client.csrf_token = csrf
    return client
