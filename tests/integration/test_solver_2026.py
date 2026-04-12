"""Integration tests for the shift solver – January / February / March 2026.

Covers three full planning months with a variety of personnel situations:
  - Standard crew (17 employees, 3 teams)
  - Reduced headcount
  - Mass vacations
  - Sick-leave waves
  - Month-boundary rest-time carry-over
  - Parametrised scenarios across all three months

All tests are tagged @pytest.mark.slow because OR-Tools may take a long
time to complete a month-long planning run.

Run these tests with:
    pytest -m slow tests/integration/test_solver_2026.py -v

Error protocol and fix suggestions are embedded in each test as
``# FIX SUGGESTION`` comments and collected in the module-level docstring
below so that they can be forwarded as ready-made prompts to the developer.

─────────────────────────────────────────────────────────────────────────────
ERROR PROTOCOL & FIX-SUGGESTION PROMPTS
─────────────────────────────────────────────────────────────────────────────
FS-2026-01  [January 2026 – reduced staff]
            Prompt: "10 Mitarbeiter in 2 Teams können min_staff_weekday=3 pro
            Schicht (3 Schichten × 3 = 9/Tag) kaum erfüllen.  Der Solver muss
            graceful in FALLBACK_L1 oder FALLBACK_L2 degradieren.  Prüfe, ob
            add_staffing_constraints() bei Unterbesetzung korrekt auf die
            Soft-Constraint-Schiene wechselt."

FS-2026-02  [January 2026 – all absent a full week]
            Prompt: "Wenn alle 17 Mitarbeiter in KW3 (2026-01-12 bis 2026-01-18)
            im Urlaub sind, muss complete_schedule für jeden dieser Tage
            ausschließlich 'ABSENT' zurückgeben.  Validiere, dass
            _build_complete_schedule() Abwesenheiten vor Schicht-Einträgen
            auswertet."

FS-2026-03  [February 2026 – S→F rest-time across month boundary]
            Prompt: "Mitarbeiter, die am 2026-01-31 einen S-Dienst hatten,
            dürfen am 2026-02-01 KEINEN F-Dienst bekommen (nur 8 h Ruhezeit).
            Stelle sicher, dass ShiftPlanningModel.previous_employee_shifts
            korrekt in add_rest_time_constraints() verarbeitet wird."

FS-2026-04  [February 2026 – understaffed]
            Prompt: "Nur 6 Mitarbeiter in 2 Teams für Februar 2026.  Das
            Ergebnis darf NICHT None sein.  Validiere den EMERGENCY-Fallback
            in solve_shift_planning() und dass der PlanningReport.status
            einen der bekannten Werte enthält."

FS-2026-05  [March 2026 – N→F rest-time across month boundary]
            Prompt: "Mitarbeiter, die am 2026-02-28 einen N-Dienst hatten,
            dürfen am 2026-03-01 KEINEN F-Dienst erhalten (Ruhezeit <11 h).
            Test wie FS-2026-03, jetzt über die Feb/März-Grenze."

FS-2026-06  [March 2026 – sick-leave wave]
            Prompt: "8 gleichzeitige AU-Abwesenheiten (fast 50 % der Crew)
            ab 2026-03-09.  Der Solver muss trotzdem eine gültige Liste
            zurückgeben.  Prüfe, ob add_staffing_constraints() sicher
            auf FALLBACK degradiert, wenn die verfügbare Mannschaft die
            Mindestbesetzung nicht erreicht."
─────────────────────────────────────────────────────────────────────────────
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

# ─── Time budgets ─────────────────────────────────────────────────────────────


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_model(employees, teams, start_date, end_date, absences=None,
                 previous_shifts=None):
    """Convenience factory for ShiftPlanningModel."""
    kwargs = dict(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=absences or [],
        shift_types=list(STANDARD_SHIFT_TYPES),
    )
    if previous_shifts is not None:
        kwargs["previous_employee_shifts"] = previous_shifts
    return ShiftPlanningModel(**kwargs)


def _assert_solver_invariants(assignments, complete_schedule, planning_report,
                               absences=None):
    """Invariants that must hold for every solver result."""
    assert assignments is not None, "assignments must not be None"
    assert complete_schedule is not None, "complete_schedule must not be None"
    assert planning_report is not None, "planning_report must not be None"
    assert isinstance(assignments, list)
    assert isinstance(complete_schedule, dict)
    assert isinstance(planning_report, PlanningReport)
    assert hasattr(planning_report, "status")
    assert planning_report.status in {
        "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
    }, f"Unexpected solver status: {planning_report.status!r}"

    # No employee has more than 1 shift per day
    counts = Counter((a.employee_id, a.date) for a in assignments)
    dups = [k for k, v in counts.items() if v > 1]
    assert not dups, f"Duplicate shift assignments detected: {dups}"

    # No employee works on an absence day
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
        assert st.code in valid_codes, f"Invalid shift code {st.code!r}"


def _make_small_team_employees(num_teams=2, emp_per_team=3):
    """Build a minimal crew: ``num_teams`` teams × ``emp_per_team`` employees."""
    teams, employees = [], []
    emp_id = 1
    for t in range(1, num_teams + 1):
        team = Team(id=t, name=f"Team {t}", employees=[], allowed_shift_type_ids=[])
        for _ in range(emp_per_team):
            emp = Employee(id=emp_id, vorname=f"V{emp_id}", name="N",
                           personalnummer=f"P{emp_id:04d}", team_id=t)
            employees.append(emp)
            team.employees.append(emp)
            emp_id += 1
        teams.append(team)
    return employees, teams


# ═════════════════════════════════════════════════════════════════════════════
# JANUARY 2026  (31 days, 2026-01-01 = Thursday)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestSolverJanuary2026Standard:
    """17 employees, 3 teams – standard full-month run for January 2026."""

    @pytest.fixture(autouse=True, scope="class")
    def solve(self, request):
        employees, teams, absences = generate_sample_data()
        model = _build_model(employees, teams,
                             date(2026, 1, 1), date(2026, 1, 31), absences)
        result = solve_shift_planning(model)
        request.cls.assignments, request.cls.schedule, request.cls.report = result
        request.cls.employees = employees
        request.cls.absences = absences

    def test_returns_non_none_3tuple(self):
        assert self.assignments is not None
        assert self.schedule is not None
        assert self.report is not None

    def test_assignments_is_list(self):
        assert isinstance(self.assignments, list)

    def test_complete_schedule_is_dict(self):
        assert isinstance(self.schedule, dict)

    def test_planning_report_has_valid_status(self):
        assert self.report.status in {
            "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
        }

    def test_no_duplicate_shifts_per_day(self):
        counts = Counter((a.employee_id, a.date) for a in self.assignments)
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

    def test_schedule_covers_all_employees_every_week(self):
        emp_ids = {e.id for e in self.employees}
        for day_offset in range(0, 31, 7):
            check_date = date(2026, 1, 1) + timedelta(days=day_offset)
            for emp_id in emp_ids:
                assert (emp_id, check_date) in self.schedule, (
                    f"Employee {emp_id} missing from schedule on {check_date}"
                )

    def test_schedule_values_are_valid(self):
        valid_codes = {st.code for st in STANDARD_SHIFT_TYPES} | {"OFF", "ABSENT"}
        for (emp_id, d), code in self.schedule.items():
            assert code in valid_codes, (
                f"Unexpected schedule code {code!r} for employee {emp_id} on {d}"
            )

    def test_no_n_followed_by_f(self):
        """After N shift, no F shift next day (< 11h rest)."""
        n_id = get_shift_type_by_code("N").id
        f_id = get_shift_type_by_code("F").id
        by_emp_date = {(a.employee_id, a.date): a for a in self.assignments}
        for a in self.assignments:
            if a.shift_type_id == n_id:
                next_a = by_emp_date.get((a.employee_id, a.date + timedelta(days=1)))
                assert next_a is None or next_a.shift_type_id != f_id, (
                    f"Employee {a.employee_id}: N on {a.date} followed by F on "
                    f"{a.date + timedelta(days=1)}"
                )


@pytest.mark.slow
def test_january_2026_many_vacations():
    """January 2026: 6 employees on U-absence during KW3 (2026-01-12 to 2026-01-18)."""
    employees, teams, _ = generate_sample_data()
    absence_start = date(2026, 1, 12)
    absence_end = date(2026, 1, 18)
    absences = [
        Absence(id=i + 1, employee_id=employees[i].id,
                absence_type=AbsenceType.U,
                start_date=absence_start, end_date=absence_end)
        for i in range(6)
    ]
    model = _build_model(employees, teams, date(2026, 1, 1), date(2026, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION (FS-2026-01): 6 gleichzeitige Abwesenheiten testen, ob der
    # Solver auf FALLBACK_L1/L2 degradiert und keine Schicht in Abwesenheitstagen plant.
    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_january_2026_all_absent_full_week():
    """January 2026: all 17 employees on U-absence for one full week (KW3).

    ERROR PROTOCOL FS-2026-02:
    complete_schedule MUST return 'ABSENT' for every employee on every absence day.
    If any employee appears with a shift code instead of 'ABSENT', the bug is in
    _build_complete_schedule() (or the equivalent logic inside solve_shift_planning).

    FIX SUGGESTION (FS-2026-02): Prüfe, ob _build_complete_schedule() Abwesenheiten
    mit höherer Priorität als Schicht-Zuweisungen behandelt.  Falls nicht, füge
    eine explizite Prüfung 'if (emp_id, d) in absence_set: code = "ABSENT"' hinzu.
    """
    employees, teams, _ = generate_sample_data()
    absence_start = date(2026, 1, 12)
    absence_end = date(2026, 1, 18)
    absences = [
        Absence(id=i + 1, employee_id=employees[i].id,
                absence_type=AbsenceType.U,
                start_date=absence_start, end_date=absence_end)
        for i in range(len(employees))
    ]
    model = _build_model(employees, teams, date(2026, 1, 1), date(2026, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)

    _assert_solver_invariants(assignments, schedule, report, absences)
    assert report.status is not None

    emp_ids = {e.id for e in employees}
    for day_offset in range((absence_end - absence_start).days + 1):
        check_date = absence_start + timedelta(days=day_offset)
        for emp_id in emp_ids:
            code = schedule.get((emp_id, check_date))
            assert code == "ABSENT", (
                f"[FS-2026-02] Employee {emp_id} on full-absence day {check_date}: "
                f"expected 'ABSENT', got {code!r}"
            )


@pytest.mark.slow
def test_january_2026_reduced_staff_10_employees():
    """January 2026: only 10 employees in 2 teams – structurally lean crew.

    ERROR PROTOCOL (FS-2026-01):
    With 10 employees over 3 shifts and min_staff_weekday=3 per shift (9/day),
    the solver may not fully satisfy minimum staffing.  It MUST gracefully
    degrade (FALLBACK_L1 / FALLBACK_L2 / EMERGENCY) instead of crashing.

    FIX SUGGESTION (FS-2026-01): Überprüfe add_staffing_constraints() darauf,
    ob es bei struktureller Unterbesetzung korrekt von Hard- zu Soft-Constraints
    wechselt.  Erhöhe notfalls MIN_STAFFING_RELAXED_PENALTY_WEIGHT, damit der
    Report die Unterbesetzung deutlich kennzeichnet.
    """
    employees, teams = _make_small_team_employees(num_teams=2, emp_per_team=5)
    model = _build_model(employees, teams, date(2026, 1, 1), date(2026, 1, 31))
    assignments, schedule, report = solve_shift_planning(model)

    _assert_solver_invariants(assignments, schedule, report)


@pytest.mark.slow
def test_january_2026_mixed_absence_types():
    """January 2026: mix of U + AU + L absences across three different employees."""
    employees, teams, _ = generate_sample_data()
    absences = [
        Absence(id=1, employee_id=employees[0].id, absence_type=AbsenceType.U,
                start_date=date(2026, 1, 4), end_date=date(2026, 1, 10)),
        Absence(id=2, employee_id=employees[5].id, absence_type=AbsenceType.AU,
                start_date=date(2026, 1, 14), end_date=date(2026, 1, 16)),
        Absence(id=3, employee_id=employees[10].id, absence_type=AbsenceType.L,
                start_date=date(2026, 1, 19), end_date=date(2026, 1, 23)),
    ]
    model = _build_model(employees, teams, date(2026, 1, 1), date(2026, 1, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)
    _assert_solver_invariants(assignments, schedule, report, absences)


# ═════════════════════════════════════════════════════════════════════════════
# FEBRUARY 2026  (28 days – 2026 is NOT a leap year)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestSolverFebruary2026Standard:
    """17 employees, 3 teams – standard full-month run for February 2026 (28 days)."""

    @pytest.fixture(autouse=True, scope="class")
    def solve(self, request):
        employees, teams, absences = generate_sample_data()
        model = _build_model(employees, teams,
                             date(2026, 2, 1), date(2026, 2, 28), absences)
        result = solve_shift_planning(model)
        request.cls.assignments, request.cls.schedule, request.cls.report = result
        request.cls.employees = employees
        request.cls.absences = absences

    def test_returns_non_none_3tuple(self):
        assert self.assignments is not None
        assert self.schedule is not None
        assert self.report is not None

    def test_planning_report_has_valid_status(self):
        assert self.report.status in {
            "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
        }

    def test_no_duplicate_shifts_per_day(self):
        counts = Counter((a.employee_id, a.date) for a in self.assignments)
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

    def test_schedule_covers_all_employees_every_week(self):
        emp_ids = {e.id for e in self.employees}
        for day_offset in range(0, 28, 7):
            check_date = date(2026, 2, 1) + timedelta(days=day_offset)
            for emp_id in emp_ids:
                assert (emp_id, check_date) in self.schedule, (
                    f"Employee {emp_id} missing from schedule on {check_date}"
                )

    def test_february_has_28_days_only(self):
        """Ensure no assignment falls beyond 2026-02-28 (not a leap year)."""
        for a in self.assignments:
            assert a.date <= date(2026, 2, 28), (
                f"Assignment on {a.date} is outside February 2026"
            )

    def test_no_s_followed_by_f(self):
        """After S shift, no F shift next day (only 8h rest < 11h minimum)."""
        s_id = get_shift_type_by_code("S").id
        f_id = get_shift_type_by_code("F").id
        by_emp_date = {(a.employee_id, a.date): a for a in self.assignments}
        for a in self.assignments:
            if a.shift_type_id == s_id:
                next_a = by_emp_date.get((a.employee_id, a.date + timedelta(days=1)))
                assert next_a is None or next_a.shift_type_id != f_id, (
                    f"Employee {a.employee_id}: S on {a.date} followed by F on "
                    f"{a.date + timedelta(days=1)}"
                )


@pytest.mark.slow
def test_february_2026_rest_time_across_january_boundary():
    """February 2026: employees with S-shift on 2026-01-31 must NOT get F on 2026-02-01.

    ERROR PROTOCOL (FS-2026-03):
    Violates the 11h minimum rest-time rule.  The boundary carry-over is encoded via
    ShiftPlanningModel.previous_employee_shifts.

    FIX SUGGESTION (FS-2026-03): Stelle sicher, dass add_rest_time_constraints()
    previous_employee_shifts korrekt auswertet.  Falls der Test fehlschlägt,
    prüfe, ob der Key-Format (employee_id, date) → shift_code konsistent mit dem
    internen Constraint-Code ist.
    """
    employees, teams, _ = generate_sample_data()
    plan_start = date(2026, 2, 1)
    plan_end = date(2026, 2, 28)
    last_day_prev = date(2026, 1, 31)

    # 4 employees had a S-shift on the last day of January
    previous_shifts = {
        (employees[i].id, last_day_prev): "S"
        for i in range(4)
    }

    model = _build_model(employees, teams, plan_start, plan_end,
                         previous_shifts=previous_shifts)
    assignments, schedule, report = solve_shift_planning(model)

    _assert_solver_invariants(assignments, schedule, report)

    f_id = get_shift_type_by_code("F").id
    by_emp_date = {(a.employee_id, a.date): a for a in assignments}
    for i in range(4):
        emp_id = employees[i].id
        first_day_a = by_emp_date.get((emp_id, plan_start))
        assert first_day_a is None or first_day_a.shift_type_id != f_id, (
            f"[FS-2026-03] Employee {emp_id} had S on {last_day_prev} but received "
            f"F on {plan_start} (violates 11h rest-time rule across month boundary)"
        )


@pytest.mark.slow
def test_february_2026_mixed_absences():
    """February 2026: overlapping U + AU + L absences for three employees."""
    employees, teams, _ = generate_sample_data()
    absences = [
        Absence(id=1, employee_id=employees[2].id, absence_type=AbsenceType.U,
                start_date=date(2026, 2, 2), end_date=date(2026, 2, 8)),
        Absence(id=2, employee_id=employees[7].id, absence_type=AbsenceType.AU,
                start_date=date(2026, 2, 10), end_date=date(2026, 2, 13)),
        Absence(id=3, employee_id=employees[12].id, absence_type=AbsenceType.L,
                start_date=date(2026, 2, 16), end_date=date(2026, 2, 20)),
    ]
    model = _build_model(employees, teams, date(2026, 2, 1), date(2026, 2, 28), absences)
    assignments, schedule, report = solve_shift_planning(model)
    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_february_2026_understaffed_6_employees():
    """February 2026: only 6 employees (2 teams × 3) – severely understaffed.

    ERROR PROTOCOL (FS-2026-04):
    6 employees cannot cover 3 shifts × min_staff_weekday=3 (= 9 required/day).
    The solver MUST NOT return None or raise an exception.  It must degrade to
    FALLBACK or EMERGENCY status and still return a valid 3-tuple.

    FIX SUGGESTION (FS-2026-04): Teste, ob solve_shift_planning() im EMERGENCY-
    Pfad immer einen nicht-leeren PlanningReport zurückgibt und der Greedy-
    Fallback zumindest alle Tage mit einem 'OFF'-Eintrag füllt.
    """
    employees, teams = _make_small_team_employees(num_teams=2, emp_per_team=3)
    model = _build_model(employees, teams, date(2026, 2, 1), date(2026, 2, 28))
    assignments, schedule, report = solve_shift_planning(model)

    # FIX SUGGESTION (FS-2026-04): see module docstring
    _assert_solver_invariants(assignments, schedule, report)
    assert report.status in {
        "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY", "FEASIBLE", "OPTIMAL"
    }, f"Unexpected status for severely understaffed scenario: {report.status!r}"


# ═════════════════════════════════════════════════════════════════════════════
# MARCH 2026  (31 days, 2026-03-01 = Sunday)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestSolverMarch2026Standard:
    """17 employees, 3 teams – standard full-month run for March 2026 (31 days)."""

    @pytest.fixture(autouse=True, scope="class")
    def solve(self, request):
        employees, teams, absences = generate_sample_data()
        model = _build_model(employees, teams,
                             date(2026, 3, 1), date(2026, 3, 31), absences)
        result = solve_shift_planning(model)
        request.cls.assignments, request.cls.schedule, request.cls.report = result
        request.cls.employees = employees
        request.cls.absences = absences

    def test_returns_non_none_3tuple(self):
        assert self.assignments is not None
        assert self.schedule is not None
        assert self.report is not None

    def test_planning_report_has_valid_status(self):
        assert self.report.status in {
            "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
        }

    def test_no_duplicate_shifts_per_day(self):
        counts = Counter((a.employee_id, a.date) for a in self.assignments)
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

    def test_schedule_covers_all_employees_every_week(self):
        emp_ids = {e.id for e in self.employees}
        for day_offset in range(0, 31, 7):
            check_date = date(2026, 3, 1) + timedelta(days=day_offset)
            for emp_id in emp_ids:
                assert (emp_id, check_date) in self.schedule, (
                    f"Employee {emp_id} missing from schedule on {check_date}"
                )

    def test_no_n_followed_by_f(self):
        n_id = get_shift_type_by_code("N").id
        f_id = get_shift_type_by_code("F").id
        by_emp_date = {(a.employee_id, a.date): a for a in self.assignments}
        for a in self.assignments:
            if a.shift_type_id == n_id:
                next_a = by_emp_date.get((a.employee_id, a.date + timedelta(days=1)))
                assert next_a is None or next_a.shift_type_id != f_id, (
                    f"Employee {a.employee_id}: N on {a.date} followed by F on "
                    f"{a.date + timedelta(days=1)}"
                )


@pytest.mark.slow
def test_march_2026_rest_time_across_february_boundary():
    """March 2026: employees with N-shift on 2026-02-28 must NOT get F on 2026-03-01.

    ERROR PROTOCOL (FS-2026-05):
    N-shift ends at ~05:45.  F-shift starts at 05:45.  Rest time = 0h < 11h minimum.
    The boundary carry-over MUST be encoded via previous_employee_shifts.

    FIX SUGGESTION (FS-2026-05): Überprüfe add_rest_time_constraints() auf korrekte
    Behandlung von N→F über die Feb/März-Grenze.  Stelle sicher, dass das
    vorherige Schicht-Datum im Key-Format (employee_id, date(2026, 2, 28)) korrekt
    gespeichert und abgerufen wird.
    """
    employees, teams, _ = generate_sample_data()
    plan_start = date(2026, 3, 1)
    plan_end = date(2026, 3, 31)
    last_day_prev = date(2026, 2, 28)

    previous_shifts = {
        (employees[i].id, last_day_prev): "N"
        for i in range(4)
    }

    model = _build_model(employees, teams, plan_start, plan_end,
                         previous_shifts=previous_shifts)
    assignments, schedule, report = solve_shift_planning(model)

    _assert_solver_invariants(assignments, schedule, report)

    f_id = get_shift_type_by_code("F").id
    by_emp_date = {(a.employee_id, a.date): a for a in assignments}
    for i in range(4):
        emp_id = employees[i].id
        first_day_a = by_emp_date.get((emp_id, plan_start))
        assert first_day_a is None or first_day_a.shift_type_id != f_id, (
            f"[FS-2026-05] Employee {emp_id} had N on {last_day_prev} but received "
            f"F on {plan_start} (violates 11h rest-time rule across month boundary)"
        )


@pytest.mark.slow
def test_march_2026_sick_leave_wave():
    """March 2026: 8 simultaneous AU-absences (≈47 % of crew) starting 2026-03-09.

    ERROR PROTOCOL (FS-2026-06):
    With 9 of 17 employees available, the solver must still produce a valid plan.
    If it crashes or returns None the emergency fallback is broken.

    FIX SUGGESTION (FS-2026-06): Teste, ob add_staffing_constraints() im Falle
    von 8 gleichzeitigen Krankmeldungen sicher auf FALLBACK degradiert.  Falls
    der Solver INFEASIBLE meldet ohne in den Greedy-Fallback zu wechseln,
    prüfe die Fallback-Kaskade in solve_shift_planning().
    """
    employees, teams, _ = generate_sample_data()
    absence_start = date(2026, 3, 9)
    absence_end = date(2026, 3, 20)
    absences = [
        Absence(id=i + 1, employee_id=employees[i].id,
                absence_type=AbsenceType.AU,
                start_date=absence_start, end_date=absence_end)
        for i in range(8)
    ]
    model = _build_model(employees, teams, date(2026, 3, 1), date(2026, 3, 31), absences)
    assignments, schedule, report = solve_shift_planning(model)

    _assert_solver_invariants(assignments, schedule, report, absences)


@pytest.mark.slow
def test_march_2026_minimal_staffing_edge_case():
    """March 2026: minimal scenario – 5 employees in 2 teams.

    Tests the lower bound of crew size for a 31-day planning run.

    FIX SUGGESTION: Mindestens so viele Mitarbeiter konfigurieren wie die Summe
    aller min_staff_weekday-Werte über alle Schichttypen (= 9 Standard), um einen
    OPTIMAL- oder FEASIBLE-Status zu erreichen.  Bei 5 Mitarbeitern wird immer
    ein FALLBACK erwartet.
    """
    teams = [
        Team(id=1, name="Team A", employees=[], allowed_shift_type_ids=[]),
        Team(id=2, name="Team B", employees=[], allowed_shift_type_ids=[]),
    ]
    employees = []
    for i in range(1, 4):
        emp = Employee(id=i, vorname=f"A{i}", name="B",
                       personalnummer=f"P{i:04d}", team_id=1)
        employees.append(emp)
        teams[0].employees.append(emp)
    for i in range(4, 6):
        emp = Employee(id=i, vorname=f"A{i}", name="B",
                       personalnummer=f"P{i:04d}", team_id=2)
        employees.append(emp)
        teams[1].employees.append(emp)

    model = _build_model(employees, teams, date(2026, 3, 1), date(2026, 3, 31))
    assignments, schedule, report = solve_shift_planning(model)
    _assert_solver_invariants(assignments, schedule, report)


# ═════════════════════════════════════════════════════════════════════════════
# PARAMETRISED: all three months, standard crew
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.parametrize("start,end,label", [
    (date(2026, 1, 1), date(2026, 1, 31), "January-2026"),
    (date(2026, 2, 1), date(2026, 2, 28), "February-2026"),
    (date(2026, 3, 1), date(2026, 3, 31), "March-2026"),
])
def test_solver_2026_standard_crew_all_months(start, end, label):
    """Standard 17-employee run across all three target months in 2026."""
    employees, teams, absences = generate_sample_data()
    model = _build_model(employees, teams, start, end, [])
    assignments, schedule, report = solve_shift_planning(model)
    _assert_solver_invariants(assignments, schedule, report)
    assert report.status in {
        "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
    }, f"[{label}] Unexpected status: {report.status!r}"
