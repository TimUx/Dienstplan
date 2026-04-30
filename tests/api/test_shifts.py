"""API tests for shift-related endpoints."""

import time

import pytest



class TestGetShiftTypes:
    def test_get_shifttypes_returns_200(self, admin_client):
        resp = admin_client.get('/api/shifttypes')
        assert resp.status_code == 200

    def test_get_shifttypes_returns_list(self, admin_client):
        data = admin_client.get('/api/shifttypes').json()
        assert isinstance(data, list)

    def test_get_shifttypes_has_standard_codes(self, admin_client):
        data = admin_client.get('/api/shifttypes').json()
        codes = {item.get('code') for item in data}
        for code in ('F', 'S', 'N'):
            assert code in codes, f"Standard shift code '{code}' not found"

    def test_get_shifttypes_have_required_fields(self, admin_client):
        data = admin_client.get('/api/shifttypes').json()
        assert len(data) > 0
        first = data[0]
        assert 'id' in first
        assert 'code' in first
        assert 'name' in first

    def test_get_single_shifttype_returns_200(self, admin_client):
        shift_types = admin_client.get('/api/shifttypes').json()
        st_id = shift_types[0]['id']
        resp = admin_client.get(f'/api/shifttypes/{st_id}')
        assert resp.status_code == 200


class TestGetSchedule:
    def test_get_schedule_with_start_date_returns_200(self, admin_client):
        resp = admin_client.get('/api/shifts/schedule?startDate=2025-01-06')
        assert resp.status_code == 200

    def test_get_schedule_without_start_date_returns_400(self, admin_client):
        resp = admin_client.get('/api/shifts/schedule')
        assert resp.status_code == 400

    def test_get_schedule_week_view(self, admin_client):
        resp = admin_client.get('/api/shifts/schedule?startDate=2025-01-06&view=week')
        assert resp.status_code == 200

    def test_get_schedule_month_view(self, admin_client):
        resp = admin_client.get('/api/shifts/schedule?startDate=2025-01-01&view=month')
        assert resp.status_code == 200

    def test_get_schedule_returns_assignments_key(self, admin_client):
        resp = admin_client.get('/api/shifts/schedule?startDate=2025-01-06')
        data = resp.json()
        # Should return a dict with assignments or similar structure
        assert isinstance(data, dict)
        assert 'assignments' in data
        assert 'metrics' in data
        assert 'processingMs' in data['metrics']

    def test_get_schedule_team_filter_only_returns_requested_team(self, admin_client):
        employees_resp = admin_client.get('/api/employees')
        employees = employees_resp.json()
        team_ids = {e.get('teamId') for e in employees if e.get('teamId')}
        if not team_ids:
            pytest.skip('No team assignments available in fixture data')

        team_id = next(iter(team_ids))
        resp = admin_client.get(f'/api/shifts/schedule?startDate=2025-01-06&teamId={team_id}')
        assert resp.status_code == 200
        data = resp.json()
        assert all(item.get('teamId') == team_id for item in data.get('assignments', []))


class TestPlanningEndpoint:
    def test_plan_as_admin_returns_job_id(self, admin_client):
        """POST /api/shifts/plan should return a job_id immediately."""
        resp = admin_client.post(
            '/api/shifts/plan?startDate=2025-03-01&endDate=2025-03-31',
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        # Should return 202 with a jobId
        assert resp.status_code == 202
        data = resp.json()
        assert 'jobId' in data

    def test_plan_without_auth_returns_401(self, client):
        csrf = client.get('/api/csrf-token').json()['token']
        resp = client.post(
            '/api/shifts/plan?startDate=2025-03-01&endDate=2025-03-31',
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 401

    def test_plan_without_csrf_returns_403(self, admin_client):
        resp = admin_client.post(
            '/api/shifts/plan?startDate=2025-03-01&endDate=2025-03-31',
        )
        assert resp.status_code == 403

    def test_plan_with_absences_does_not_fail_with_date_nameerror(self, admin_client):
        """
        Regression test for planning worker scope bug:
        NameError: name 'date' is not defined.
        """
        resp = admin_client.post(
            '/api/shifts/plan?startDate=2026-02-01&endDate=2026-02-28&force=false',
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 202
        job_id = resp.json().get('jobId')
        assert job_id

        deadline = time.monotonic() + 45
        status_payload = {}
        status = 'running'

        while status == 'running' and time.monotonic() < deadline:
            time.sleep(0.2)
            status_resp = admin_client.get(
                f'/api/shifts/plan/status/{job_id}',
                headers={'X-CSRF-Token': admin_client.csrf_token},
            )
            assert status_resp.status_code == 200
            status_payload = status_resp.json()
            status = status_payload.get('status', 'running')

        assert status != 'running', f"Planning job {job_id} did not finish in time: {status_payload}"

        details = (status_payload.get('details') or '')
        message = (status_payload.get('message') or '')
        assert "name 'date' is not defined" not in details
        assert "name 'date' is not defined" not in message
