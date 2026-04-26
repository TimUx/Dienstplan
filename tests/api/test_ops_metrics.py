"""API tests for operational metrics endpoints."""


def test_ops_metrics_requires_admin(client):
    response = client.get('/api/ops/metrics')
    assert response.status_code == 401


def test_ops_metrics_returns_metrics_payload(admin_client):
    response = admin_client.get('/api/ops/metrics')
    assert response.status_code == 200
    data = response.json()
    assert 'metrics' in data
    assert 'planning_jobs_started' in data['metrics']
    assert 'uptime_seconds' in data['metrics']


def test_ops_metrics_increase_when_planning_job_started(admin_client):
    before = admin_client.get('/api/ops/metrics').json()['metrics']['planning_jobs_started']
    response = admin_client.post(
        '/api/shifts/plan?startDate=2025-03-01&endDate=2025-03-31',
        headers={'X-CSRF-Token': admin_client.csrf_token},
    )
    assert response.status_code == 202
    after = admin_client.get('/api/ops/metrics').json()['metrics']['planning_jobs_started']
    assert after >= before + 1
