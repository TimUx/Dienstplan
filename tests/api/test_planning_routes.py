"""API tests for planning report routes (read-only, auth-gated)."""

import pytest


@pytest.mark.api
class TestPlanningReport:
    def test_report_requires_auth(self, client):
        r = client.get("/api/planning/report/2025/3")
        assert r.status_code == 401

    def test_invalid_month_returns_400(self, admin_client):
        r = admin_client.get("/api/planning/report/2025/13")
        assert r.status_code == 400

    def test_missing_report_returns_404(self, admin_client):
        r = admin_client.get("/api/planning/report/2099/1")
        assert r.status_code == 404

    def test_summary_requires_auth(self, client):
        r = client.get("/api/planning/report/2025/3/summary")
        assert r.status_code == 401
