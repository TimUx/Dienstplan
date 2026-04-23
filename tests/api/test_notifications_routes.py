"""API tests for admin/disponent notification endpoints."""

import pytest


@pytest.mark.api
class TestNotifications:
    def test_list_requires_auth(self, client):
        r = client.get("/api/notifications")
        assert r.status_code == 401

    def test_admin_can_list_notifications(self, admin_client):
        r = admin_client.get("/api/notifications?limit=5")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_count_requires_auth(self, client):
        r = client.get("/api/notifications/count")
        assert r.status_code == 401

    def test_admin_notification_count(self, admin_client):
        r = admin_client.get("/api/notifications/count")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert isinstance(data["count"], int)
