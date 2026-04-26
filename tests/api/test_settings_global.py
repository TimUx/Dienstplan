"""API tests for global shift-planning settings."""

import pytest


@pytest.mark.api
class TestGlobalSettings:
    def test_get_global_settings_requires_auth(self, client):
        r = client.get("/api/settings/global")
        assert r.status_code == 401

    def test_get_global_settings_returns_defaults_shape(self, admin_client):
        r = admin_client.get("/api/settings/global")
        assert r.status_code == 200
        data = r.json()
        assert "minRestHoursBetweenShifts" in data

    def test_put_requires_admin(self, client):
        csrf = client.get("/api/csrf-token").json()["token"]
        r = client.put(
            "/api/settings/global",
            json={"minRestHoursBetweenShifts": 11},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 401

    def test_put_validates_min_rest_bounds(self, admin_client):
        r = admin_client.put(
            "/api/settings/global",
            json={"minRestHoursBetweenShifts": 4},
            headers={"X-CSRF-Token": admin_client.csrf_token},
        )
        assert r.status_code == 400

    def test_put_accepts_valid_min_rest(self, admin_client):
        r = admin_client.put(
            "/api/settings/global",
            json={"minRestHoursBetweenShifts": 12},
            headers={"X-CSRF-Token": admin_client.csrf_token},
        )
        assert r.status_code == 200
        assert r.json().get("success") is True
