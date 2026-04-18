"""API tests for the health check endpoint."""

import pytest
from types import SimpleNamespace



class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_health_status_is_healthy(self, client):
        data = client.get('/api/health').json()
        assert data['status'] == 'healthy'

    def test_health_has_db_field(self, client):
        data = client.get('/api/health').json()
        assert 'db' in data

    def test_health_db_is_ok(self, client):
        data = client.get('/api/health').json()
        assert data['db'] == 'ok'

    def test_health_has_python_field(self, client):
        data = client.get('/api/health').json()
        assert 'python' in data

    def test_health_has_ortools_field(self, client):
        data = client.get('/api/health').json()
        assert 'ortools' in data

    def test_health_python_version_is_string(self, client):
        data = client.get('/api/health').json()
        assert isinstance(data['python'], str)
        assert len(data['python']) > 0

    def test_health_ortools_version_is_string(self, client):
        data = client.get('/api/health').json()
        assert isinstance(data['ortools'], str)

    def test_health_has_version_field(self, client):
        data = client.get('/api/health').json()
        assert 'version' in data

    def test_health_no_auth_required(self, client):
        """Health endpoint is publicly accessible."""
        resp = client.get('/api/health')
        assert resp.status_code == 200


class TestHealthMetadataHelper:
    def test_last_merge_uses_merge_commit_date(self, monkeypatch):
        from api import health

        outputs = [
            SimpleNamespace(returncode=0, stdout='2026-04-18T10:15:30+00:00\n'),
        ]

        def fake_run(*args, **kwargs):
            return outputs.pop(0)

        monkeypatch.setattr(health.subprocess, 'run', fake_run)

        assert health._get_last_merge_or_commit_iso() == '2026-04-18T10:15:30+00:00'

    def test_last_merge_falls_back_to_latest_commit(self, monkeypatch):
        from api import health

        outputs = [
            SimpleNamespace(returncode=0, stdout='\n'),
            SimpleNamespace(returncode=0, stdout='2026-04-17T08:00:00+00:00\n'),
        ]

        def fake_run(*args, **kwargs):
            return outputs.pop(0)

        monkeypatch.setattr(health.subprocess, 'run', fake_run)

        assert health._get_last_merge_or_commit_iso() == '2026-04-17T08:00:00+00:00'

    def test_last_merge_returns_unknown_if_git_fails(self, monkeypatch):
        from api import health

        def fake_run(*args, **kwargs):
            raise RuntimeError('git unavailable')

        monkeypatch.setattr(health.subprocess, 'run', fake_run)

        assert health._get_last_merge_or_commit_iso() == 'unknown'
