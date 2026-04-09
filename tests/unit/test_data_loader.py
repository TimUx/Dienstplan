"""Unit tests for the data_loader module."""

import pytest
from datetime import date


from data_loader import generate_sample_data
from entities import AbsenceType, Employee, Team, Absence


class TestGenerateSampleData:
    @pytest.fixture(autouse=True)
    def load_data(self):
        self.employees, self.teams, self.absences = generate_sample_data()

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------

    def test_returns_17_employees(self):
        assert len(self.employees) == 17

    def test_returns_3_teams(self):
        assert len(self.teams) == 3

    def test_all_employees_have_team_id(self):
        for emp in self.employees:
            assert emp.team_id is not None, (
                f"Employee {emp.full_name} has no team_id"
            )

    def test_no_duplicate_employee_ids(self):
        ids = [emp.id for emp in self.employees]
        assert len(ids) == len(set(ids))

    def test_no_duplicate_personalnummern(self):
        pnrs = [emp.personalnummer for emp in self.employees]
        assert len(pnrs) == len(set(pnrs))

    def test_all_employees_have_names(self):
        for emp in self.employees:
            assert emp.vorname, f"Employee {emp.id} has no first name"
            assert emp.name, f"Employee {emp.id} has no last name"

    def test_employee_types_are_correct(self):
        for emp in self.employees:
            assert isinstance(emp, Employee)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def test_teams_have_employees_list(self):
        for team in self.teams:
            assert isinstance(team.employees, list)
            assert len(team.employees) > 0, f"Team {team.name} has no employees"

    def test_all_17_employees_assigned_to_teams(self):
        total = sum(len(t.employees) for t in self.teams)
        assert total == 17

    def test_team_employee_ids_match_main_list(self):
        all_emp_ids = {emp.id for emp in self.employees}
        for team in self.teams:
            for emp in team.employees:
                assert emp.id in all_emp_ids

    def test_team_types_are_correct(self):
        for team in self.teams:
            assert isinstance(team, Team)

    def test_teams_have_unique_ids(self):
        ids = [t.id for t in self.teams]
        assert len(ids) == len(set(ids))

    # ------------------------------------------------------------------
    # Absences
    # ------------------------------------------------------------------

    def test_absences_are_list(self):
        assert isinstance(self.absences, list)

    def test_absences_use_valid_absence_types(self):
        valid_codes = {e.value for e in AbsenceType}  # {"AU", "U", "L"}
        for absence in self.absences:
            assert absence.absence_type.value in valid_codes, (
                f"Absence {absence.id} uses invalid type {absence.absence_type}"
            )

    def test_absence_dates_are_valid_ranges(self):
        for absence in self.absences:
            assert absence.start_date <= absence.end_date, (
                f"Absence {absence.id}: start {absence.start_date} > end {absence.end_date}"
            )

    def test_absence_employee_ids_reference_known_employees(self):
        known_ids = {emp.id for emp in self.employees}
        for absence in self.absences:
            assert absence.employee_id in known_ids, (
                f"Absence {absence.id} references unknown employee {absence.employee_id}"
            )

    def test_absence_types_are_correct(self):
        for absence in self.absences:
            assert isinstance(absence, Absence)

    def test_no_duplicate_absence_ids(self):
        if self.absences:
            ids = [a.id for a in self.absences]
            assert len(ids) == len(set(ids))
