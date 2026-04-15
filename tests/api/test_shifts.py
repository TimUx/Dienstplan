"""API tests for shift-related endpoints."""

import pytest



class TestGetShiftTypes:
    def test_get_shifttypes_returns_200(self, client):
        resp = client.get('/api/shifttypes')
        assert resp.status_code == 200

    def test_get_shifttypes_returns_list(self, client):
        data = client.get('/api/shifttypes').json()
        assert isinstance(data, list)

    def test_get_shifttypes_has_standard_codes(self, client):
        data = client.get('/api/shifttypes').json()
        codes = {item.get('code') for item in data}
        for code in ('F', 'S', 'N'):
            assert code in codes, f"Standard shift code '{code}' not found"

    def test_get_shifttypes_have_required_fields(self, client):
        data = client.get('/api/shifttypes').json()
        assert len(data) > 0
        first = data[0]
        assert 'id' in first
        assert 'code' in first
        assert 'name' in first

    def test_get_single_shifttype_returns_200(self, client):
        shift_types = client.get('/api/shifttypes').json()
        st_id = shift_types[0]['id']
        resp = client.get(f'/api/shifttypes/{st_id}')
        assert resp.status_code == 200


class TestGetSchedule:
    def test_get_schedule_with_start_date_returns_200(self, client):
        resp = client.get('/api/shifts/schedule?startDate=2025-01-06')
        assert resp.status_code == 200

    def test_get_schedule_without_start_date_returns_400(self, client):
        resp = client.get('/api/shifts/schedule')
        assert resp.status_code == 400

    def test_get_schedule_week_view(self, client):
        resp = client.get('/api/shifts/schedule?startDate=2025-01-06&view=week')
        assert resp.status_code == 200

    def test_get_schedule_month_view(self, client):
        resp = client.get('/api/shifts/schedule?startDate=2025-01-01&view=month')
        assert resp.status_code == 200

    def test_get_schedule_returns_assignments_key(self, client):
        resp = client.get('/api/shifts/schedule?startDate=2025-01-06')
        data = resp.json()
        # Should return a dict with assignments or similar structure
        assert isinstance(data, dict)


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
