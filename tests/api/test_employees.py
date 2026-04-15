"""API tests for employee CRUD endpoints."""

import pytest



class TestGetEmployees:
    def test_get_employees_returns_200(self, client):
        resp = client.get('/api/employees')
        assert resp.status_code == 200

    def test_get_employees_returns_list(self, client):
        resp = client.get('/api/employees')
        data = resp.json()
        assert isinstance(data, list)

    def test_get_employees_has_sample_data(self, client):
        resp = client.get('/api/employees')
        data = resp.json()
        # Sample data has at least 17 employees
        assert len(data) >= 17

    def test_get_employees_have_required_fields(self, client):
        resp = client.get('/api/employees')
        employees = resp.json()
        assert len(employees) > 0
        first = employees[0]
        assert 'id' in first
        assert 'vorname' in first
        assert 'name' in first
        assert 'personalnummer' in first

    def test_get_employee_by_id(self, client):
        # Get all first then fetch one
        employees = client.get('/api/employees').json()
        emp_id = employees[0]['id']
        resp = client.get(f'/api/employees/{emp_id}')
        assert resp.status_code == 200

    def test_get_nonexistent_employee_returns_404(self, client):
        resp = client.get('/api/employees/999999')
        assert resp.status_code == 404


class TestCreateEmployee:
    def _new_emp(self, suffix="001"):
        return {
            'vorname': 'Test',
            'name': 'Employee',
            'personalnummer': f'TST{suffix}',
            'email': f'test.employee{suffix}@example.com',
            'password': 'SecurePass123!',
        }

    def test_create_without_auth_returns_401(self, client):
        csrf = client.get('/api/csrf-token').json()['token']
        resp = client.post(
            '/api/employees',
            json=self._new_emp(),
            headers={'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 401

    def test_create_as_admin_returns_201(self, admin_client):
        resp = admin_client.post(
            '/api/employees',
            json=self._new_emp("002"),
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 201

    def test_create_employee_returns_id(self, admin_client):
        resp = admin_client.post(
            '/api/employees',
            json=self._new_emp("003"),
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        data = resp.json()
        assert 'id' in data

    def test_missing_name_returns_400(self, admin_client):
        payload = self._new_emp("004")
        del payload['name']
        resp = admin_client.post(
            '/api/employees',
            json=payload,
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400

    def test_missing_personalnummer_returns_400(self, admin_client):
        payload = self._new_emp("005")
        del payload['personalnummer']
        resp = admin_client.post(
            '/api/employees',
            json=payload,
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400

    def test_duplicate_personalnummer_returns_400(self, admin_client):
        payload = self._new_emp("006")
        admin_client.post(
            '/api/employees',
            json=payload,
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        # Create same personalnummer again
        payload2 = self._new_emp("006")
        payload2['email'] = 'other.email@example.com'
        resp = admin_client.post(
            '/api/employees',
            json=payload2,
            headers={'X-CSRF-Token': admin_client.csrf_token},
        )
        assert resp.status_code == 400

    def test_create_without_csrf_returns_403(self, admin_client):
        resp = admin_client.post('/api/employees', json=self._new_emp("007"))
        assert resp.status_code == 403


class TestGetTeams:
    def test_get_teams_returns_200(self, client):
        resp = client.get('/api/teams')
        assert resp.status_code == 200

    def test_get_teams_returns_list(self, client):
        resp = client.get('/api/teams')
        data = resp.json()
        assert isinstance(data, list)

    def test_get_teams_has_sample_data(self, client):
        resp = client.get('/api/teams')
        data = resp.json()
        assert len(data) >= 3
