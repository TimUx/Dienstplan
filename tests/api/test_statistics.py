"""API tests for statistics dashboard endpoint."""

import sqlite3


def _get_test_employee_id(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Id FROM Employees WHERE Email != ? ORDER BY Id LIMIT 1",
            ("admin@fritzwinter.de",)
        )
        return cursor.fetchone()[0]


def _get_absence_type_id(db_path, code):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ?", (code,))
        return cursor.fetchone()[0]


def _clear_employee_data(db_path, employee_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ShiftAssignments WHERE EmployeeId = ?", (employee_id,))
        cursor.execute("DELETE FROM Absences WHERE EmployeeId = ?", (employee_id,))
        conn.commit()


def _set_weekly_hours(db_path, hours):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ShiftTypes SET WeeklyWorkingHours = ?", (hours,))
        conn.commit()


class TestDashboardStatistics:
    def test_absence_days_are_clipped_to_selected_period_and_include_vacation(self, client, test_db):
        employee_id = _get_test_employee_id(test_db)
        urlaub_type_id = _get_absence_type_id(test_db, 'U')
        _clear_employee_data(test_db, employee_id)

        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Absences (EmployeeId, Type, AbsenceTypeId, StartDate, EndDate)
                VALUES (?, 2, ?, '2025-01-25', '2025-02-05')
            """, (employee_id, urlaub_type_id))
            conn.commit()

        resp = client.get('/api/statistics/dashboard?startDate=2025-02-01&endDate=2025-02-28')
        assert resp.status_code == 200
        data = resp.json()

        entry = next(item for item in data['employeeAbsenceDays'] if item['employeeId'] == employee_id)
        assert entry['totalDays'] == 5
        assert entry['byType'].get('U') == 5

    def test_au_urlaub_lehrgang_absence_hours_are_capped_to_six_days_per_week(self, client, test_db):
        employee_id = _get_test_employee_id(test_db)
        au_type_id = _get_absence_type_id(test_db, 'AU')
        _clear_employee_data(test_db, employee_id)
        _set_weekly_hours(test_db, 48.0)

        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Absences (EmployeeId, Type, AbsenceTypeId, StartDate, EndDate)
                VALUES (?, 1, ?, '2025-02-03', '2025-02-09')
            """, (employee_id, au_type_id))
            conn.commit()

        resp = client.get('/api/statistics/dashboard?startDate=2025-02-01&endDate=2025-02-28')
        assert resp.status_code == 200
        data = resp.json()

        entry = next(item for item in data['employeeWorkHours'] if item['employeeId'] == employee_id)
        assert entry['totalHours'] == 48.0
