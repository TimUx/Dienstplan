"""API tests for absence management endpoints."""

import pytest



def _get_first_employee_id(client):
    """Retrieve the first employee id from the API."""
    employees = client.get('/api/employees').get_json()
    return employees[0]['id']


class TestGetAbsences:
    def test_get_absences_returns_200(self, client):
        resp = client.get('/api/absences')
        assert resp.status_code == 200

    def test_get_absences_returns_list(self, client):
        resp = client.get('/api/absences')
        data = resp.get_json()
        assert isinstance(data, list)

    def test_get_absences_no_auth_required(self, client):
        """Absences GET is publicly readable."""
        resp = client.get('/api/absences')
        assert resp.status_code == 200


class TestGetAbsenceTypes:
    def test_get_absence_types_returns_200(self, client):
        resp = client.get('/api/absencetypes')
        assert resp.status_code == 200

    def test_get_absence_types_returns_list(self, client):
        data = client.get('/api/absencetypes').get_json()
        assert isinstance(data, list)

    def test_absence_types_contain_standard_codes(self, client):
        data = client.get('/api/absencetypes').get_json()
        codes = [item.get('code') for item in data]
        for expected in ('U', 'AU', 'L'):
            assert expected in codes, f"Standard absence code '{expected}' not found"

    def test_absence_types_have_required_fields(self, client):
        data = client.get('/api/absencetypes').get_json()
        assert len(data) > 0
        first = data[0]
        assert 'id' in first or 'Id' in first
        assert 'code' in first or 'Code' in first


class TestCreateAbsence:
    def _absence_payload(self, employee_id):
        return {
            'employeeId': employee_id,
            'type': 2,   # U = vacation
            'startDate': '2025-03-10',
            'endDate': '2025-03-14',
        }

    def test_create_without_auth_returns_401(self, client):
        emp_id = _get_first_employee_id(client)
        csrf = client.get('/api/csrf-token').get_json()['token']
        resp = client.post(
            '/api/absences',
            json=self._absence_payload(emp_id),
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 401

    def test_create_as_admin_returns_201(self, admin_client):
        emp_id = _get_first_employee_id(admin_client)
        resp = admin_client.post(
            '/api/absences',
            json=self._absence_payload(emp_id),
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 201

    def test_create_returns_absence_id(self, admin_client):
        emp_id = _get_first_employee_id(admin_client)
        resp = admin_client.post(
            '/api/absences',
            json=self._absence_payload(emp_id),
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        data = resp.get_json()
        assert 'id' in data

    def test_create_without_csrf_returns_403(self, admin_client):
        emp_id = _get_first_employee_id(admin_client)
        resp = admin_client.post(
            '/api/absences',
            json=self._absence_payload(emp_id),
        )
        assert resp.status_code == 403

    def test_missing_employee_id_returns_400(self, admin_client):
        resp = admin_client.post(
            '/api/absences',
            json={'type': 2, 'startDate': '2025-03-10', 'endDate': '2025-03-14'},
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400

    def test_missing_start_date_returns_400(self, admin_client):
        emp_id = _get_first_employee_id(admin_client)
        resp = admin_client.post(
            '/api/absences',
            json={'employeeId': emp_id, 'type': 2, 'endDate': '2025-03-14'},
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400

    def test_missing_end_date_returns_400(self, admin_client):
        emp_id = _get_first_employee_id(admin_client)
        resp = admin_client.post(
            '/api/absences',
            json={'employeeId': emp_id, 'type': 2, 'startDate': '2025-03-10'},
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400
