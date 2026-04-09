"""API tests for authentication endpoints."""

import pytest

import sys
sys.path.insert(0, '/home/runner/work/Dienstplan/Dienstplan')

ADMIN_EMAIL = "admin@fritzwinter.de"
ADMIN_PASSWORD = "Admin123!"


# ---------------------------------------------------------------------------
# CSRF token endpoint
# ---------------------------------------------------------------------------

class TestCsrfToken:
    def test_get_csrf_token_returns_200(self, client):
        resp = client.get('/api/csrf-token')
        assert resp.status_code == 200

    def test_get_csrf_token_returns_token(self, client):
        resp = client.get('/api/csrf-token')
        data = resp.get_json()
        assert 'token' in data
        assert len(data['token']) > 0

    def test_csrf_token_is_string(self, client):
        resp = client.get('/api/csrf-token')
        assert isinstance(resp.get_json()['token'], str)


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------

class TestLogin:
    def _csrf(self, client):
        return client.get('/api/csrf-token').get_json()['token']

    def test_valid_login_returns_200(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 200

    def test_valid_login_returns_success_true(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
            headers={'X-CSRF-Token': csrf},
        )
        data = resp.get_json()
        assert data.get('success') is True

    def test_valid_login_returns_user_data(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
            headers={'X-CSRF-Token': csrf},
        )
        data = resp.get_json()
        assert 'user' in data
        assert data['user']['email'] == ADMIN_EMAIL

    def test_invalid_password_returns_401(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': 'wrongpassword'},
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': 'unknown@example.com', 'password': 'anything'},
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 401

    def test_login_without_csrf_token_returns_403(self, client):
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
        )
        assert resp.status_code == 403

    def test_login_missing_email_returns_400(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'password': ADMIN_PASSWORD},
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 400

    def test_login_missing_password_returns_400(self, client):
        csrf = self._csrf(client)
        resp = client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL},
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Current user endpoint
# ---------------------------------------------------------------------------

class TestCurrentUser:
    def test_no_auth_returns_401(self, client):
        resp = client.get('/api/auth/current-user')
        assert resp.status_code == 401

    def test_authenticated_returns_200(self, admin_client):
        resp = admin_client.get('/api/auth/current-user')
        assert resp.status_code == 200

    def test_authenticated_returns_user_email(self, admin_client):
        resp = admin_client.get('/api/auth/current-user')
        data = resp.get_json()
        assert 'email' in data or ('user' in data and 'email' in data['user'])

    def test_sets_session_on_login(self, client):
        csrf = client.get('/api/csrf-token').get_json()['token']
        client.post(
            '/api/auth/login',
            json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
            headers={'X-CSRF-Token': csrf},
        )
        with client.session_transaction() as sess:
            assert 'user_id' in sess


# ---------------------------------------------------------------------------
# Logout endpoint
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_returns_200(self, admin_client):
        resp = admin_client.post(
            '/api/auth/logout',
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 200

    def test_logout_clears_session(self, admin_client):
        admin_client.post(
            '/api/auth/logout',
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        with admin_client.session_transaction() as sess:
            assert 'user_id' not in sess

    def test_subsequent_current_user_returns_401_after_logout(self, admin_client):
        admin_client.post(
            '/api/auth/logout',
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        resp = admin_client.get('/api/auth/current-user')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin-only endpoint (roles)
# ---------------------------------------------------------------------------

class TestAdminAccess:
    def test_get_roles_as_admin_returns_200(self, admin_client):
        resp = admin_client.get('/api/roles')
        assert resp.status_code == 200

    def test_get_roles_unauthenticated_returns_401(self, client):
        resp = client.get('/api/roles')
        assert resp.status_code == 401
