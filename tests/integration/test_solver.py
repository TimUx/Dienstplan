"""Integration tests for the shift solver.

All solver tests are marked @pytest.mark.slow because OR-Tools can take
up to time_limit_seconds to complete.

Run fast tests only:  pytest -m "not slow"
Run all tests:        pytest -m slow tests/integration/test_solver.py
"""

import pytest
from datetime import date, timedelta
from collections import Counter


from entities import (
    Employee, Team, Absence, AbsenceType, ShiftAssignment,
    STANDARD_SHIFT_TYPES, get_shift_type_by_code,
)
from data_loader import generate_sample_data
from model import ShiftPlanningModel
from solver import solve_shift_planning
from planning_report import PlanningReport

FAST_LIMIT = 120   # seconds for simple scenarios
SLOW_LIMIT = 300   # seconds for complex scenarios


def _build_model(employees, teams, start_date, end_date, absences=None):
    return ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=absences or [],
        shift_types=list(STANDARD_SHIFT_TYPES),
    )


def _assert_solver_invariants(assignments, complete_schedule, planning_report, absences=None):
    """Common assertions that must hold for any solver result."""
    assert assignments is not None, "assignments must not be None"
    assert complete_schedule is not None, "complete_schedule must not be None"
    assert planning_report is not None, "planning_report must not be None"
    assert isinstance(assignments, list)
    assert isinstance(complete_schedule, dict)
    assert isinstance(planning_report, PlanningReport)
    assert hasattr(planning_report, 'status')

    # No employee has more than 1 shift per day
    emp_day = [(a.employee_id, a.date) for a in assignments]
    counts = Counter(emp_day)
    dups = [k for k, v in counts.items() if v > 1]
    assert not dups, f"Duplicate shift assignments detected: {dups}"

    # No employee works on absence days
    if absences:
        absence_days = {
            (a.employee_id, a.start_date + timedelta(days=i))
            for a in absences
            for i in range((a.end_date - a.start_date).days + 1)
        }
        for assignment in assignments:
            assert (assignment.employee_id, assignment.date) not in absence_days, (
                f"Employee {assignment.employee_id} worked on absence day {assignment.date}"
            )

    # All shift codes are valid
    valid_codes = {st.code for st in STANDARD_SHIFT_TYPES}
    for a in assignments:
        st = next((s for s in STANDARD_SHIFT_TYPES if s.id == a.shift_type_id), None)
        assert st is not None, f"Unknown shift_type_id {a.shift_type_id}"
        assert st.code in valid_codes


# ---------------------------------------------------------------------------
# Basic scenarios
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestSolverBasicScenario:
    """17 employees, 3 teams, January 2025 (31 days)."""

    @pytest.fixture(autouse=True, scope="class")
    def solve(self, request):
        employees, teams, absences = generate_sample_data()
        model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
        result = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
        request.cls.assignments, request.cls.schedule, request.cls.report = result
        request.cls.absences = absences

    def test_returns_non_none_3tuple(self):
        assert self.assignments is not None
        assert self.schedule is not None
        assert self.report is not None

    def test_assignments_is_list(self):
        assert isinstance(self.assignments, list)

    def test_complete_schedule_is_dict(self):
        assert isinstance(self.schedule, dict)

    def test_planning_report_has_status(self):
        assert hasattr(self.report, 'status')
        assert self.report.status in {"OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"}

    def test_no_duplicate_shifts_per_day(self):
        emp_day = [(a.employee_id, a.date) for a in self.assignments]
        counts = Counter(emp_day)
        dups = [k for k, v in counts.items() if v > 1]
        assert not dups, f"Duplicate assignments: {dups}"

    def test_no_work_during_absences(self):
        absence_days = {
            (a.employee_id, a.start_date + timedelta(days=i))
            for a in self.absences
            for i in range((a.end_date - a.start_date).days + 1)
        }
        for assignment in self.assignments:
            assert (assignment.employee_id, assignment.date) not in absence_days


@pytest.mark.slow
@pytest.mark.parametrize("start,end,label", [
    (date(2025, 2, 1), date(2025, 2, 28), "February-28days"),
    (date(2025, 4, 1), date(2025, 4, 30), "April-30days"),
    (date(2025, 1, 1), date(2025, 1, 31), "January-31days"),
    (date(2024, 12, 31), date(2025, 1, 2), "CrossMonthBoundary"),
])
def test_solver_various_periods(start, end, label):
    """Solver works for different planning period lengths."""
    employees, teams, absences = generate_sample_data()
    model = _build_model(employees, teams, start, end, [])
    assignments, schedule, report = solve_shift_planning(
        model, time_limit_seconds=FAST_LIMIT
    )
    _assert_solver_invariants(assignments, schedule, report)


# ---------------------------------------------------------------------------
# Absence scenarios
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_solver_many_vacations():
    """6 employees on U-absence simultaneously."""
    employees, teams, _ = generate_sample_data()
    start, end = date(2025, 1, 6), date(2025, 1, 12)
    # Put employees from different teams on vacation
    absences = [
        Absence(id=i + 1, employee_id=employees[i].id,
                absence_type=AbsenceType.U,
                start_date=start, end_date=end)
        for i in range(6)
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_solver_multiple_sick_leaves():
    """4 employees on AU absence simultaneously."""
    employees, teams, _ = generate_sample_data()
    start, end = date(2025, 1, 13), date(2025, 1, 17)
    absences = [
        Absence(id=i + 1, employee_id=employees[i].id,
                absence_type=AbsenceType.AU,
                start_date=start, end_date=end)
        for i in range(4)
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_solver_training_absences():
    """2 employees on L (Lehrgang) absence."""
    employees, teams, _ = generate_sample_data()
    absences = [
        Absence(id=1, employee_id=employees[0].id,
                absence_type=AbsenceType.L,
                start_date=date(2025, 1, 6), end_date=date(2025, 1, 10)),
        Absence(id=2, employee_id=employees[1].id,
                absence_type=AbsenceType.L,
                start_date=date(2025, 1, 6), end_date=date(2025, 1, 8)),
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_solver_combined_absences():
    """Mix of U + AU + L in the same planning period."""
    employees, teams, _ = generate_sample_data()
    absences = [
        Absence(id=1, employee_id=employees[0].id, absence_type=AbsenceType.U,
                start_date=date(2025, 1, 6), end_date=date(2025, 1, 12)),
        Absence(id=2, employee_id=employees[5].id, absence_type=AbsenceType.AU,
                start_date=date(2025, 1, 8), end_date=date(2025, 1, 10)),
        Absence(id=3, employee_id=employees[10].id, absence_type=AbsenceType.L,
                start_date=date(2025, 1, 13), end_date=date(2025, 1, 17)),
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report, absences)


# ---------------------------------------------------------------------------
# Edge-case scenarios
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_solver_minimum_staffing_edge_case():
    """Minimal scenario: 5 employees in 2 teams."""
    teams = [
        Team(id=1, name="Team A", employees=[], allowed_shift_type_ids=[]),
        Team(id=2, name="Team B", employees=[], allowed_shift_type_ids=[]),
    ]
    employees = []
    for i in range(1, 4):
        emp = Employee(id=i, vorname=f"A{i}", name="B", personalnummer=f"P{i:04d}", team_id=1)
        employees.append(emp)
        teams[0].employees.append(emp)
    for i in range(4, 6):
        emp = Employee(id=i, vorname=f"A{i}", name="B", personalnummer=f"P{i:04d}", team_id=2)
        employees.append(emp)
        teams[1].employees.append(emp)

    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report)


@pytest.mark.slow
def test_solver_with_springer():
    """Employee with no team_id (Springer) is handled."""
    employees, teams, _ = generate_sample_data()
    # Detach one employee from their team
    springer = employees[0]
    orig_team_id = springer.team_id
    springer.team_id = None
    # Remove from team employees list too
    for team in teams:
        team.employees = [e for e in team.employees if e.id != springer.id]

    try:
        model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
        assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
        _assert_solver_invariants(assignments, schedule, report)
    finally:
        # Restore for other tests
        springer.team_id = orig_team_id


@pytest.mark.slow
def test_solver_cross_team_assignment():
    """Teams with explicit allowed_shift_type_ids."""
    employees, teams, absences = generate_sample_data()
    # Set allowed shifts on all teams
    f_id = get_shift_type_by_code("F").id
    s_id = get_shift_type_by_code("S").id
    n_id = get_shift_type_by_code("N").id
    for team in teams:
        team.allowed_shift_type_ids = [f_id, s_id, n_id]

    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)
    _assert_solver_invariants(assignments, schedule, report, absences)


# ---------------------------------------------------------------------------
# Consistency and validity checks
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_solver_returns_consistent_results():
    """Running the solver twice both return non-None 3-tuples."""
    employees, teams, _ = generate_sample_data()
    model1 = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    r1 = solve_shift_planning(model1, time_limit_seconds=FAST_LIMIT)
    assert r1 is not None
    assert len(r1) == 3

    model2 = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    r2 = solve_shift_planning(model2, time_limit_seconds=FAST_LIMIT)
    assert r2 is not None
    assert len(r2) == 3


@pytest.mark.slow
def test_solver_complete_schedule_contains_all_employees():
    """complete_schedule has an entry for every employee on every planning day."""
    employees, teams, _ = generate_sample_data()
    start, end = date(2025, 1, 1), date(2025, 1, 31)
    model = _build_model(employees, teams, start, end)
    assignments, schedule, report = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)

    emp_ids = {e.id for e in employees}
    # Check at least a few days within the original planning period
    for day_offset in range(0, 31, 7):
        check_date = start + timedelta(days=day_offset)
        for emp_id in emp_ids:
            assert (emp_id, check_date) in schedule, (
                f"Employee {emp_id} missing from schedule on {check_date}"
            )


@pytest.mark.slow
def test_solver_schedule_values_are_valid():
    """complete_schedule values are one of the expected codes."""
    employees, teams, _ = generate_sample_data()
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    _, schedule, _ = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)

    valid_codes = {st.code for st in STANDARD_SHIFT_TYPES} | {"OFF", "ABSENT"}
    for (emp_id, d), code in schedule.items():
        assert code in valid_codes, f"Unexpected schedule code '{code}' for employee {emp_id} on {d}"


@pytest.mark.slow
def test_solver_forbidden_nacht_to_frueh_not_in_result():
    """After N shift, no F shift assigned next day (0h rest violates 11h rule)."""
    employees, teams, _ = generate_sample_data()
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    assignments, _, _ = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)

    n_id = get_shift_type_by_code("N").id
    f_id = get_shift_type_by_code("F").id

    by_emp_date = {(a.employee_id, a.date): a for a in assignments}
    for a in assignments:
        if a.shift_type_id == n_id:
            next_day = a.date + timedelta(days=1)
            next_a = by_emp_date.get((a.employee_id, next_day))
            assert next_a is None or next_a.shift_type_id != f_id, (
                f"Employee {a.employee_id}: N on {a.date} followed by F on {next_day}"
            )


@pytest.mark.slow
def test_solver_forbidden_spaet_to_frueh_not_in_result():
    """After S shift, no F shift assigned next day (8h rest < 11h minimum)."""
    employees, teams, _ = generate_sample_data()
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31))
    assignments, _, _ = solve_shift_planning(model, time_limit_seconds=SLOW_LIMIT)

    s_id = get_shift_type_by_code("S").id
    f_id = get_shift_type_by_code("F").id

    by_emp_date = {(a.employee_id, a.date): a for a in assignments}
    for a in assignments:
        if a.shift_type_id == s_id:
            next_day = a.date + timedelta(days=1)
            next_a = by_emp_date.get((a.employee_id, next_day))
            assert next_a is None or next_a.shift_type_id != f_id, (
                f"Employee {a.employee_id}: S on {a.date} followed by F on {next_day}"
            )
