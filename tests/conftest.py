"""Shared fixtures for the Dienstplan test suite."""

import pytest
import os


from datetime import date
from entities import (
    Employee, Team, Absence, AbsenceType, ShiftAssignment,
    STANDARD_SHIFT_TYPES,
)
from data_loader import generate_sample_data


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
    initialize_database(db_path, with_sample_data=True)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def app(test_db):
    """Flask test application."""
    from web_api import create_app
    flask_app = create_app(test_db)
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Authenticated admin test client with CSRF token."""
    resp = client.get('/api/csrf-token')
    csrf = resp.get_json()['token']
    client.post(
        '/api/auth/login',
        json={'email': 'admin@fritzwinter.de', 'password': 'Admin123!'},
        headers={'X-CSRF-Token': csrf},
    )
    client.csrf_token = csrf
    return client
