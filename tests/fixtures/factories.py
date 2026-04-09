"""Factory functions for building test data objects."""

from datetime import date, timedelta
from entities import (
    Employee, Team, Absence, AbsenceType, ShiftAssignment, ShiftType,
    STANDARD_SHIFT_TYPES, get_shift_type_by_code,
)


def make_employee(
    id: int = 1,
    vorname: str = "Max",
    name: str = "Mustermann",
    personalnummer: str = None,
    team_id: int = 1,
    is_td_qualified: bool = False,
    is_brandmeldetechniker: bool = False,
    is_brandschutzbeauftragter: bool = False,
    is_team_leader: bool = False,
) -> Employee:
    pnr = personalnummer or f"P{id:04d}"
    return Employee(
        id=id,
        vorname=vorname,
        name=name,
        personalnummer=pnr,
        team_id=team_id,
        is_td_qualified=is_td_qualified,
        is_brandmeldetechniker=is_brandmeldetechniker,
        is_brandschutzbeauftragter=is_brandschutzbeauftragter,
        is_team_leader=is_team_leader,
    )


def make_team(
    id: int = 1,
    name: str = "Team Alpha",
    employees: list = None,
    allowed_shift_type_ids: list = None,
) -> Team:
    return Team(
        id=id,
        name=name,
        employees=employees or [],
        allowed_shift_type_ids=allowed_shift_type_ids or [],
    )


def make_absence(
    id: int = 1,
    employee_id: int = 1,
    absence_type: AbsenceType = AbsenceType.U,
    start_date: date = None,
    end_date: date = None,
) -> Absence:
    start = start_date or date(2025, 1, 6)
    end = end_date or (start + timedelta(days=6))
    return Absence(
        id=id,
        employee_id=employee_id,
        absence_type=absence_type,
        start_date=start,
        end_date=end,
    )


def make_assignment(
    id: int = 1,
    employee_id: int = 1,
    shift_type_id: int = 1,
    d: date = None,
) -> ShiftAssignment:
    return ShiftAssignment(
        id=id,
        employee_id=employee_id,
        shift_type_id=shift_type_id,
        date=d or date(2025, 1, 6),
    )


def make_small_scenario(num_teams: int = 2, emp_per_team: int = 3):
    """Build a minimal scenario: ``num_teams`` teams with ``emp_per_team`` each."""
    teams = []
    employees = []
    emp_id = 1
    for t in range(1, num_teams + 1):
        team = make_team(id=t, name=f"Team {t}")
        for _ in range(emp_per_team):
            emp = make_employee(id=emp_id, team_id=t, personalnummer=f"P{emp_id:04d}")
            employees.append(emp)
            team.employees.append(emp)
            emp_id += 1
        teams.append(team)
    return employees, teams
