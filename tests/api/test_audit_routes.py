"""API tests for audit log endpoints (Admin)."""

import pytest


@pytest.mark.api
class TestStatisticsAuditLogs:
    """Legacy path: ``/api/auditlogs`` on statistics router."""

    def test_requires_admin(self, client):
        r = client.get("/api/auditlogs?page=1&pageSize=10")
        assert r.status_code == 401

    def test_admin_gets_json_envelope(self, admin_client):
        r = admin_client.get("/api/auditlogs?page=1&pageSize=10")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "totalCount" in data


@pytest.mark.api
class TestAuditRouter:
    """Newer path: ``/api/audit-logs`` on audit router."""

    def test_requires_admin(self, client):
        r = client.get("/api/audit-logs")
        assert r.status_code == 401

    def test_admin_gets_paginated_data(self, admin_client):
        r = admin_client.get("/api/audit-logs?page=1&limit=20")
        assert r.status_code == 200
        data = r.json()
        assert "data" in data
        assert "total" in data
