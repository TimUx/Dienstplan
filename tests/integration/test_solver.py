"""Integration tests for the shift solver.

All solver tests are marked @pytest.mark.slow because OR-Tools may take
a long time to complete.

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
        result = solve_shift_planning(model)
        request.cls.assignments, request.cls.schedule, request.cls.report = result
        request.cls.absences = absences
        request.cls.employees = employees

    def test_returns_non_none_3tuple(self):
        assert self.assignments is not None
        assert self.schedule is not None
        assert self.report is not None
        assert self.employees, "employees list must not be empty"

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

    def test_schedule_covers_all_employees(self):
        """complete_schedule has an entry for every employee on every planning day."""
        emp_ids = {e.id for e in self.employees}
        start = date(2025, 1, 1)
        for day_offset in range(0, 31, 7):
            check_date = start + timedelta(days=day_offset)
            for emp_id in emp_ids:
                assert (emp_id, check_date) in self.schedule, (
                    f"Employee {emp_id} missing from schedule on {check_date}"
                )

    def test_schedule_values_are_valid(self):
        """complete_schedule values are one of the expected codes."""
        valid_codes = {st.code for st in STANDARD_SHIFT_TYPES} | {"OFF", "ABSENT"}
        for (emp_id, d), code in self.schedule.items():
            assert code in valid_codes, (
                f"Unexpected schedule code '{code}' for employee {emp_id} on {d}"
            )

    def test_no_n_followed_by_f(self):
        """After N shift, no F shift assigned next day (violates 11h rest rule)."""
        n_id = get_shift_type_by_code("N").id
        f_id = get_shift_type_by_code("F").id
        by_emp_date = {(a.employee_id, a.date): a for a in self.assignments}
        for a in self.assignments:
            if a.shift_type_id == n_id:
                next_day = a.date + timedelta(days=1)
                next_a = by_emp_date.get((a.employee_id, next_day))
                assert next_a is None or next_a.shift_type_id != f_id, (
                    f"Employee {a.employee_id}: N on {a.date} followed by F on {next_day}"
                )

    def test_no_s_followed_by_f(self):
        """After S shift, no F shift assigned next day (8h rest < 11h minimum)."""
        s_id = get_shift_type_by_code("S").id
        f_id = get_shift_type_by_code("F").id
        by_emp_date = {(a.employee_id, a.date): a for a in self.assignments}
        for a in self.assignments:
            if a.shift_type_id == s_id:
                next_day = a.date + timedelta(days=1)
                next_a = by_emp_date.get((a.employee_id, next_day))
                assert next_a is None or next_a.shift_type_id != f_id, (
                    f"Employee {a.employee_id}: S on {a.date} followed by F on {next_day}"
                )


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
    assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
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
        assignments, schedule, report = solve_shift_planning(model)
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
    assignments, schedule, report = solve_shift_planning(model)
    _assert_solver_invariants(assignments, schedule, report, absences)


# ---------------------------------------------------------------------------
# Stress / Fehler-Situationen
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_solver_too_few_employees_infeasible():
    """Scenario 1: Only 2 employees in 1 team – structurally understaffed.

    Standard min_staff_weekday=3 cannot be met with just 2 employees.
    The solver must gracefully fall back instead of crashing or returning None.
    """
    team = Team(id=1, name="Tiny Team", employees=[], allowed_shift_type_ids=[])
    employees = []
    for i in range(1, 3):
        emp = Employee(id=i, vorname=f"X{i}", name="Y", personalnummer=f"P{i:04d}", team_id=1)
        employees.append(emp)
        team.employees.append(emp)

    model = _build_model(employees, [team], date(2025, 1, 1), date(2025, 1, 31))
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Mindestens so viele Mitarbeiter konfigurieren wie
    # min_staff_weekday + min_staff_weekend über alle Schichttypen gefordert werden.
    _assert_solver_invariants(assignments, schedule, report)
    assert report.status in {"FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"}, (
        f"Expected a fallback status for structurally understaffed scenario, got: {report.status!r}"
    )


@pytest.mark.slow
def test_solver_all_employees_absent_entire_week():
    """Scenario 2: All 17 employees on vacation for one full week (2025-01-13 to 2025-01-19).

    The solver cannot assign any shifts during that week.
    complete_schedule must show 'ABSENT' for every employee on every absence day.
    """
    employees, teams, _ = generate_sample_data()
    absence_start = date(2025, 1, 13)
    absence_end = date(2025, 1, 19)
    absences = [
        Absence(
            id=i + 1,
            employee_id=employees[i].id,
            absence_type=AbsenceType.U,
            start_date=absence_start,
            end_date=absence_end,
        )
        for i in range(len(employees))
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Prüfe vor dem Solve, ob in einer Woche < min_staff_weekday
    # verfügbare Mitarbeiter existieren, und warne den Dispatcher vorab.
    _assert_solver_invariants(assignments, schedule, report, absences)
    assert report.status is not None, "Planning report must always have a non-None status"

    emp_ids = {e.id for e in employees}
    for day_offset in range((absence_end - absence_start).days + 1):
        check_date = absence_start + timedelta(days=day_offset)
        for emp_id in emp_ids:
            code = schedule.get((emp_id, check_date))
            assert code == "ABSENT", (
                f"Employee {emp_id} on full-absence day {check_date}: "
                f"expected 'ABSENT', got {code!r}"
            )


@pytest.mark.slow
def test_solver_rest_time_cross_month_boundary():
    """Scenario 3: 4 employees had S-shift on the last day of the previous month.

    previous_employee_shifts signals that they ended January with Spätdienst.
    The solver must respect the 11h rest-time rule and NOT assign an F-shift
    on the first day of February for those employees.
    """
    employees, teams, _ = generate_sample_data()
    plan_start = date(2025, 2, 1)
    plan_end = date(2025, 2, 28)
    last_day_prev = date(2025, 1, 31)

    previous_shifts = {
        (employees[i].id, last_day_prev): "S"
        for i in range(4)
    }

    model = ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=plan_start,
        end_date=plan_end,
        absences=[],
        shift_types=list(STANDARD_SHIFT_TYPES),
        previous_employee_shifts=previous_shifts,
    )
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Übergib dem Solver stets previous_employee_shifts mit dem
    # vollständigen letzten Monat, damit Ruhezeit-Grenzen über Monatsgrenzen
    # korrekt eingehalten werden.
    _assert_solver_invariants(assignments, schedule, report)

    f_id = get_shift_type_by_code("F").id
    by_emp_date = {(a.employee_id, a.date): a for a in assignments}
    for i in range(4):
        emp_id = employees[i].id
        first_day_assignment = by_emp_date.get((emp_id, plan_start))
        assert first_day_assignment is None or first_day_assignment.shift_type_id != f_id, (
            f"Employee {emp_id} had S on {last_day_prev} but received F on {plan_start} "
            f"(violates 11h rest-time rule across month boundary)"
        )


@pytest.mark.slow
def test_solver_duplicate_absence_ids():
    """Scenario 4: Two Absence objects share the same ID for the same employee with overlapping dates.

    The solver must not crash. No shift may be assigned to the affected employee
    on any day covered by either absence.
    """
    employees, teams, _ = generate_sample_data()
    emp = employees[0]
    absences = [
        Absence(
            id=999, employee_id=emp.id, absence_type=AbsenceType.U,
            start_date=date(2025, 1, 6), end_date=date(2025, 1, 10),
        ),
        Absence(
            id=999, employee_id=emp.id, absence_type=AbsenceType.AU,
            start_date=date(2025, 1, 8), end_date=date(2025, 1, 14),
        ),
    ]
    model = _build_model(employees, teams, date(2025, 1, 1), date(2025, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Im Preprocessing (vor ShiftPlanningModel-Konstruktion) Absence-Duplikate
    # per {employee_id, date}-Set deduplizieren, um doppelte Constraint-Registrierungen im
    # CP-SAT Modell zu vermeiden.
    _assert_solver_invariants(assignments, schedule, report)

    covered_days = set()
    for absence in absences:
        for i in range((absence.end_date - absence.start_date).days + 1):
            covered_days.add(absence.start_date + timedelta(days=i))

    for assignment in assignments:
        if assignment.employee_id == emp.id:
            assert assignment.date not in covered_days, (
                f"Employee {emp.id} assigned on absence day {assignment.date} "
                f"despite overlapping duplicate absences"
            )


@pytest.mark.slow
def test_solver_single_day_planning_period():
    """Scenario 5: Planning period of exactly 1 day (Wednesday 2025-01-15).

    The week-extension logic in ShiftPlanningModel must handle a 1-day span
    without producing a negative date range. complete_schedule must contain
    an entry for every employee on that specific day.
    """
    employees, teams, _ = generate_sample_data()
    single_day = date(2025, 1, 15)  # Wednesday
    model = _build_model(employees, teams, single_day, single_day)
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Sicherstellen, dass die Wochenerweiterungslogik in ShiftPlanningModel
    # auch für 0- oder 1-Tages-Spannen korrekt funktioniert (kein negativer Datumsbereich).
    _assert_solver_invariants(assignments, schedule, report)

    emp_ids = {e.id for e in employees}
    for emp_id in emp_ids:
        assert (emp_id, single_day) in schedule, (
            f"Employee {emp_id} missing from complete_schedule on the single planning day {single_day}"
        )


@pytest.mark.slow
def test_solver_all_employees_without_team():
    """Scenario 6: All employees have team_id=None and the teams list is empty.

    Extreme Springer scenario – every employee is detached from any team.
    The solver must not abort; it must return a valid (possibly empty) result.
    """
    employees, _, _ = generate_sample_data()
    for emp in employees:
        emp.team_id = None

    model = _build_model(employees, [], date(2025, 1, 1), date(2025, 1, 31))
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION: Mindestens 1 Fallback-Team oder generische Springer-Schicht-Zuweisung
    # für teamlose Mitarbeiter implementieren, um die Planungsqualität zu verbessern.
    _assert_solver_invariants(assignments, schedule, report)


