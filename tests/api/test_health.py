"""API tests for the health check endpoint."""

import pytest



class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_health_status_is_healthy(self, client):
        data = client.get('/api/health').get_json()
        assert data['status'] == 'healthy'

    def test_health_has_db_field(self, client):
        data = client.get('/api/health').get_json()
        assert 'db' in data

    def test_health_db_is_ok(self, client):
        data = client.get('/api/health').get_json()
        assert data['db'] == 'ok'

    def test_health_has_python_field(self, client):
        data = client.get('/api/health').get_json()
        assert 'python' in data

    def test_health_has_ortools_field(self, client):
        data = client.get('/api/health').get_json()
        assert 'ortools' in data

    def test_health_python_version_is_string(self, client):
        data = client.get('/api/health').get_json()
        assert isinstance(data['python'], str)
        assert len(data['python']) > 0

    def test_health_ortools_version_is_string(self, client):
        data = client.get('/api/health').get_json()
        assert isinstance(data['ortools'], str)

    def test_health_has_version_field(self, client):
        data = client.get('/api/health').get_json()
        assert 'version' in data

    def test_health_no_auth_required(self, client):
        """Health endpoint is publicly accessible."""
        resp = client.get('/api/health')
        assert resp.status_code == 200
