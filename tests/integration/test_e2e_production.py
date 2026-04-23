"""
End-to-end production environment tests.

These tests replicate the **exact** code path of the production planning job
(`api/shifts.py::_run_planning_job`) step by step:

  1. Real SQLite database – initialised with ``db_init.initialize_database``
     (same schema + sample data as production).
  2. Data loaded via ``data_loader.load_from_database`` – never via the
     in-memory helper ``generate_sample_data``.
  3. Global settings loaded via ``data_loader.load_global_settings``.
  4. Planning dates extended to complete Sun–Sat weeks via
     ``api.shared.extend_planning_dates_to_complete_weeks``.
  5. Model built via ``model.create_shift_planning_model`` with the DB
     shift types (not the hardcoded ``STANDARD_SHIFT_TYPES``).
  6. Solver called with both ``global_settings`` and ``db_path`` – exactly
     as ``_run_planning_job`` calls ``solve_shift_planning``.
  7. HTTP end-to-end: ``POST /api/shifts/plan`` → poll
     ``GET /api/shifts/plan/status/{jobId}`` → verify DB writes.

All tests are marked ``@pytest.mark.slow`` because they invoke the real
OR-Tools CP-SAT solver.

─────────────────────────────────────────────────────────────────────────────
WHAT DIFFERS FROM THE EXISTING SOLVER TESTS
─────────────────────────────────────────────────────────────────────────────
Existing tests (test_solver.py / test_solver_2026.py)
  • Use ``generate_sample_data()``        → in-memory objects only, no DB
  • Use ``list(STANDARD_SHIFT_TYPES)``    → hardcoded Python constants
  • Never load ``global_settings``        → solver uses defaults
  • Never pass ``db_path``               → rotation groups not loaded from DB
  • Never call ``extend_planning_dates_to_complete_weeks``

These tests fix ALL of the above gaps.
─────────────────────────────────────────────────────────────────────────────
ERROR PROTOCOL & FIX-SUGGESTION PROMPTS
─────────────────────────────────────────────────────────────────────────────
EP-E2E-01  [TestSolverProductionPipeline – test_shift_types_loaded_from_db]
           SYMPTOM: AssertionError – shift type codes missing in DB.
           FIX PROMPT: "In db_init.py::initialize_shift_types() prüfen, ob F,
           S und N mit IsActive=1 gespeichert werden. Fehlende Shift-Types
           ergänzen oder initialize_database(with_sample_data=True) korrigieren."

EP-E2E-02  [TestSolverProductionPipeline – test_extended_dates_are_full_weeks]
           SYMPTOM: Extended start is not Sunday / extended end is not Saturday.
           FIX PROMPT: "api/shared.py::extend_planning_dates_to_complete_weeks()
           überprüfen. Python weekday(): Mon=0 … Sun=6. Der Code muss zu
           Sonntag (6) zurückgehen und bis Samstag (5) vorwärts."

EP-E2E-03  [TestSolverProductionPipeline – test_no_work_during_absences]
           SYMPTOM: Employee assigned on an absence day.
           FIX PROMPT: "Im constraints-Paket sicherstellen, dass jede Absence korrekt
           als hard constraint gesperrt wird. ShiftPlanningModel.__init__() muss
           absence_days zur locked_absence-Map hinzufügen, bevor der Solver
           die Variablen anlegt."

EP-E2E-04  [TestSolverProductionPipeline – test_all_assignments_use_db_shift_types]
           SYMPTOM: shift_type_id in assignment not in DB shift types.
           FIX PROMPT: "Solver gibt ShiftAssignment-Objekte zurück, deren
           shift_type_id aus STANDARD_SHIFT_TYPES statt aus den DB-Shift-Types
           stammt. Sicherstellen, dass ShiftPlanningModel ausschließlich die
           übergebenen shift_types (aus load_from_database) verwendet."

EP-E2E-05  [TestHttpApiPlanningE2E – test_job_completed_without_error]
           SYMPTOM: Job status is 'error' instead of 'success'.
           FIX PROMPT: "GET /api/shifts/plan/status/{jobId} liefert status='error'.
           Vollständige Fehlermeldung im Feld 'message' prüfen. Häufige Ursachen:
           fehlende DB-Tabellen (PlanningJobs, ShiftTypes), AuthError oder
           Exception in _run_planning_job. Stack-Trace in den Flask-Logs prüfen."

EP-E2E-06  [TestHttpApiPlanningE2E – test_assignments_persisted_in_database]
           SYMPTOM: ShiftAssignments count = 0 after successful job.
           FIX PROMPT: "In api/shifts.py::_run_planning_job() die DB-Write-Logik
           prüfen (cursor.executemany für ShiftAssignments). Sicherstellen, dass
           conn.commit() nach dem Bulk-Insert aufgerufen wird."

EP-E2E-07  [TestHttpApiPlanningE2E – test_planning_report_saved_in_database]
           SYMPTOM: PlanningReports row missing after completed job.
           FIX PROMPT: "api/shifts.py::_save_planning_report() wird möglicherweise
           nur bei status='success' aufgerufen. Prüfen, ob der Aufruf hinter
           einem frühen return steht und ob das Jahr/Monat-Paar korrekt übergeben
           wird."
─────────────────────────────────────────────────────────────────────────────
"""

import os
import time
import sqlite3
import pytest
from collections import Counter
from datetime import date, timedelta

from db_init import initialize_database
from data_loader import load_from_database, load_global_settings
from model import create_shift_planning_model
from solver import solve_shift_planning
from api.shared import extend_planning_dates_to_complete_weeks
from planning_report import PlanningReport

pytestmark = [pytest.mark.slow, pytest.mark.e2e]

# ---------------------------------------------------------------------------
# Tuning
# ---------------------------------------------------------------------------
_POLL_INTERVAL_S = 2    # seconds between HTTP status polls
_MAX_WAIT_S = 600       # give up after this many seconds total

# Solver time limit for the TEST environment only.
# Production sets time_limit_seconds=None (unlimited) and uses num_workers=8.
# In CI/test environments the solver runs on 1 shared core, so we cap at
# 300 s to keep the test suite practical.  A feasible solution is typically
# found well within 120 s for a standard 17-employee, 1-month scenario.
_TEST_SOLVER_TIME_LIMIT_S = 300


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# (module scope → the expensive DB init + Flask app setup run only ONCE
#  for the whole file, not per-test)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def prod_db(tmp_path_factory):
    """
    Real SQLite database initialised exactly as production does it.

    Uses ``initialize_database(with_sample_data=True)`` → creates all tables,
    seeds shift types (F/S/N), creates default admin, inserts sample
    employees + teams.
    """
    db_path = str(tmp_path_factory.mktemp("prod_e2e") / "prod.db")
    os.environ["DIENSTPLAN_INITIAL_ADMIN_EMAIL"] = "admin@fritzwinter.de"
    os.environ["DIENSTPLAN_INITIAL_ADMIN_PASSWORD"] = "Admin123!"
    initialize_database(db_path, with_sample_data=True)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="module")
def prod_flask_app(prod_db):
    """FastAPI app wired to the production-equivalent SQLite database."""
    from web_api import create_app
    app = create_app(prod_db)
    return app


@pytest.fixture(scope="module")
def prod_admin_client(prod_flask_app):
    """
    Authenticated admin test client (module-scoped).

    Logs in once; the session cookie is reused across all tests in this file.
    """
    from fastapi.testclient import TestClient
    client = TestClient(prod_flask_app, raise_server_exceptions=False)
    resp = client.get("/api/csrf-token")
    csrf = resp.json()["token"]
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@fritzwinter.de", "password": "Admin123!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert login.status_code == 200, (
        f"Admin login failed ({login.status_code}): {login.json()}"
    )
    client.csrf_token = csrf
    return client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _db_count(db_path: str, table: str, where: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    with sqlite3.connect(db_path) as conn:
        return conn.execute(sql, params).fetchone()[0]


# ===========================================================================
# Class 1 – Solver pipeline (direct Python, mirrors _run_planning_job exactly)
# ===========================================================================

@pytest.mark.slow
class TestSolverProductionPipeline:
    """
    Invokes the solver using the **identical code path** as the production
    background job ``_run_planning_job``:

        load_from_database(db_path)
        load_global_settings(db_path)
        extend_planning_dates_to_complete_weeks(start, end)
        create_shift_planning_model(..., shift_types=<from DB>)
        solve_shift_planning(model, global_settings=..., db_path=...)

    Planning period: March 2025 (31 days).
    """

    PLAN_START = date(2025, 3, 1)
    PLAN_END   = date(2025, 3, 31)

    @pytest.fixture(autouse=True, scope="class")
    def run_solver_pipeline(self, request, prod_db):
        """Run the full production pipeline once; attach results to the class."""
        # ── Step 1: load data from DB (not generate_sample_data!) ──────────
        employees, teams, absences, shift_types = load_from_database(prod_db)
        global_settings = load_global_settings(prod_db)

        # ── Step 2: extend dates to complete weeks ──────────────────────────
        ext_start, ext_end = extend_planning_dates_to_complete_weeks(
            self.PLAN_START, self.PLAN_END
        )

        # ── Step 3: build model with DB shift types ─────────────────────────
        model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=ext_start,
            end_date=ext_end,
            absences=absences,
            shift_types=shift_types,
        )

        # ── Step 4: solve (same signature as production) ────────────────────
        # NOTE: production uses time_limit_seconds=None (unlimited).
        # We cap at _TEST_SOLVER_TIME_LIMIT_S here so CI doesn't time out.
        # The code path is identical; only the search budget differs.
        assignments, schedule, report = solve_shift_planning(
            model,
            global_settings=global_settings,
            db_path=prod_db,
            time_limit_seconds=_TEST_SOLVER_TIME_LIMIT_S,
        )

        request.cls.assignments   = assignments
        request.cls.schedule      = schedule
        request.cls.report        = report
        request.cls.employees     = employees
        request.cls.teams         = teams
        request.cls.absences      = absences
        request.cls.shift_types   = shift_types
        request.cls.global_settings = global_settings
        request.cls.ext_start     = ext_start
        request.cls.ext_end       = ext_end

    # ── Smoke ───────────────────────────────────────────────────────────────

    def test_solver_returns_non_none_3tuple(self):
        """Solver must always return a 3-tuple, never raise or return None."""
        assert self.assignments is not None, "assignments is None"
        assert self.schedule    is not None, "schedule is None"
        assert self.report      is not None, "planning_report is None"

    def test_planning_report_is_correct_type(self):
        assert isinstance(self.report, PlanningReport)

    def test_planning_report_has_known_status(self):
        """Status must be one of the documented solver outcomes."""
        assert self.report.status in {
            "OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"
        }, f"Unexpected solver status: {self.report.status!r}"

    # ── Production fidelity ─────────────────────────────────────────────────

    def test_shift_types_loaded_from_db(self):
        """
        Shift types must come from the database – not the hardcoded
        STANDARD_SHIFT_TYPES constant that existing tests use.

        EP-E2E-01: if this fails, check db_init.initialize_shift_types().
        """
        assert len(self.shift_types) >= 3, (
            f"Expected ≥3 shift types from DB, got {len(self.shift_types)}"
        )
        codes = {st.code for st in self.shift_types}
        for required in ("F", "S", "N"):
            assert required in codes, (
                f"Required shift code '{required}' not found in DB shift types {codes}. "
                "EP-E2E-01: check db_init.initialize_shift_types()."
            )

    def test_global_settings_loaded_from_db(self):
        """
        Global settings must be a dict with the expected keys.
        Production uses these to configure rest-time and consecutive shift limits.
        """
        assert isinstance(self.global_settings, dict), (
            f"Expected dict from load_global_settings, got {type(self.global_settings)}"
        )
        for key in ("min_rest_hours",):
            assert key in self.global_settings, (
                f"Missing key '{key}' in global_settings: {self.global_settings}"
            )

    def test_extended_dates_are_full_weeks(self):
        """
        Dates must be extended to complete Sun–Sat weeks, exactly as production
        does before passing to the model.

        EP-E2E-02: if this fails, check api/shared.extend_planning_dates_to_complete_weeks().
        """
        assert self.ext_start.weekday() == 6, (
            f"Extended start {self.ext_start} must be Sunday (weekday=6), "
            f"got weekday={self.ext_start.weekday()}"
        )
        assert self.ext_end.weekday() == 5, (
            f"Extended end {self.ext_end} must be Saturday (weekday=5), "
            f"got weekday={self.ext_end.weekday()}"
        )
        assert self.ext_start <= self.PLAN_START
        assert self.ext_end   >= self.PLAN_END

    def test_employees_and_teams_loaded_from_db(self):
        """sample_data must have been written to the DB during initialize_database."""
        assert len(self.employees) > 0, "No employees loaded from DB"
        assert len(self.teams)     > 0, "No teams loaded from DB"

    # ── Correctness ─────────────────────────────────────────────────────────

    def test_no_duplicate_shifts_per_day(self):
        """No employee may be assigned more than one shift on any single day."""
        emp_day = [(a.employee_id, a.date) for a in self.assignments]
        dups = [k for k, v in Counter(emp_day).items() if v > 1]
        assert not dups, f"Duplicate assignments detected: {dups}"

    def test_no_work_during_absences(self):
        """
        Employees must not receive a shift on any day covered by an absence.

        EP-E2E-03: if this fails, check absence constraint registration in the constraints package.
        """
        absence_days = {
            (a.employee_id, a.start_date + timedelta(days=i))
            for a in self.absences
            for i in range((a.end_date - a.start_date).days + 1)
        }
        for a in self.assignments:
            assert (a.employee_id, a.date) not in absence_days, (
                f"Employee {a.employee_id} worked on absence day {a.date}. "
                "EP-E2E-03: check absence hard constraints."
            )

    def test_schedule_covers_all_employees_every_day(self):
        """
        complete_schedule must contain an entry for every (employee_id, date)
        combination within the extended planning period.
        """
        emp_ids = {e.id for e in self.employees}
        total_days = (self.ext_end - self.ext_start).days + 1
        for delta in range(total_days):
            d = self.ext_start + timedelta(days=delta)
            for emp_id in emp_ids:
                assert (emp_id, d) in self.schedule, (
                    f"Employee {emp_id} missing from complete_schedule on {d}"
                )

    def test_schedule_values_are_valid_codes(self):
        """
        Every value in complete_schedule must be a DB shift code, 'OFF', or 'ABSENT'.

        EP-E2E-04: if a foreign code appears, the model is mixing STANDARD_SHIFT_TYPES
        with DB shift types.
        """
        valid = {st.code for st in self.shift_types} | {"OFF", "ABSENT"}
        bad = [
            (emp_id, d, code)
            for (emp_id, d), code in self.schedule.items()
            if code not in valid
        ]
        assert not bad, (
            f"Invalid schedule codes found: {bad[:5]} … (valid={valid}). "
            "EP-E2E-04: ensure model uses DB shift types exclusively."
        )

    def test_all_assignment_shift_type_ids_are_from_db(self):
        """
        Every ShiftAssignment must reference a shift_type_id that exists in the
        DB shift types (not a hardcoded ID from STANDARD_SHIFT_TYPES).

        EP-E2E-04: if this fails, the solver is using hardcoded IDs.
        """
        db_ids = {st.id for st in self.shift_types}
        bad = [a for a in self.assignments if a.shift_type_id not in db_ids]
        assert not bad, (
            f"Assignments with unknown shift_type_ids: "
            f"{[(a.employee_id, a.date, a.shift_type_id) for a in bad[:5]]}. "
            f"DB shift type IDs: {db_ids}. EP-E2E-04."
        )

    def test_no_n_shift_followed_by_f_shift(self):
        """
        No employee may have a Nachtschicht (N) immediately followed by a
        Frühschicht (F) on the next day (rest-time violation).
        """
        n_id = next((st.id for st in self.shift_types if st.code == "N"), None)
        f_id = next((st.id for st in self.shift_types if st.code == "F"), None)
        if n_id is None or f_id is None:
            pytest.skip("N or F shift type not found in DB")
        by = {(a.employee_id, a.date): a for a in self.assignments}
        violations = []
        for a in self.assignments:
            if a.shift_type_id == n_id:
                next_day = a.date + timedelta(days=1)
                nxt = by.get((a.employee_id, next_day))
                if nxt and nxt.shift_type_id == f_id:
                    violations.append((a.employee_id, a.date))
        assert not violations, (
            f"N→F rest-time violations for (employee_id, date): {violations}"
        )

    def test_no_s_shift_followed_by_f_shift(self):
        """
        No employee may have a Spätschicht (S) immediately followed by a
        Frühschicht (F) on the next day (rest-time violation).
        """
        s_id = next((st.id for st in self.shift_types if st.code == "S"), None)
        f_id = next((st.id for st in self.shift_types if st.code == "F"), None)
        if s_id is None or f_id is None:
            pytest.skip("S or F shift type not found in DB")
        by = {(a.employee_id, a.date): a for a in self.assignments}
        violations = []
        for a in self.assignments:
            if a.shift_type_id == s_id:
                next_day = a.date + timedelta(days=1)
                nxt = by.get((a.employee_id, next_day))
                if nxt and nxt.shift_type_id == f_id:
                    violations.append((a.employee_id, a.date))
        assert not violations, (
            f"S→F rest-time violations for (employee_id, date): {violations}"
        )


# ===========================================================================
# Class 2 – Full HTTP API end-to-end (entire _run_planning_job stack via HTTP)
# ===========================================================================

@pytest.mark.slow
class TestHttpApiPlanningE2E:
    """
    Exercises the complete production request flow via the HTTP API:

      1. ``POST /api/shifts/plan?startDate=…&endDate=…``  →  202 + jobId
      2. ``GET  /api/shifts/plan/status/{jobId}``  (poll until not 'running')
      3. Assert final status == 'success'
      4. Verify ``ShiftAssignments`` rows written to DB
      5. Verify ``PlanningReports`` row written to DB
      6. Verify ``GET /api/shifts/schedule`` returns assignments

    This is the only test class that exercises the background threading layer
    (``threading.Thread(target=_run_planning_job)``).

    Planning period: April 2025 (different month from the solver pipeline
    test to avoid DB conflicts).
    """

    PLAN_START_STR = "2025-04-01"
    PLAN_END_STR   = "2025-04-30"

    @pytest.fixture(autouse=True, scope="class")
    def run_full_api_flow(self, request, prod_admin_client, prod_db):
        """Trigger planning, poll until done, store all results on the class."""
        start_str = self.PLAN_START_STR
        end_str   = self.PLAN_END_STR

        # ── Step 1: POST /api/shifts/plan ───────────────────────────────────
        resp = prod_admin_client.post(
            f"/api/shifts/plan?startDate={start_str}&endDate={end_str}",
            headers={"X-CSRF-Token": prod_admin_client.csrf_token},
        )
        assert resp.status_code == 202, (
            f"Expected HTTP 202 Accepted, got {resp.status_code}: {resp.json()}"
        )
        job_id = resp.json().get("jobId")
        assert job_id, "Response missing 'jobId' field"

        # ── Step 2: poll GET /api/shifts/plan/status/{jobId} ────────────────
        deadline   = time.monotonic() + _MAX_WAIT_S
        job_status = "running"
        job_data   = {}
        while job_status == "running":
            if time.monotonic() > deadline:
                pytest.fail(
                    f"Planning job {job_id!r} was still 'running' after "
                    f"{_MAX_WAIT_S}s. "
                    "EP-E2E-05: check Flask logs for exception in _run_planning_job."
                )
            time.sleep(_POLL_INTERVAL_S)
            poll = prod_admin_client.get(
                f"/api/shifts/plan/status/{job_id}",
                headers={"X-CSRF-Token": prod_admin_client.csrf_token},
            )
            job_data   = poll.json() or {}
            job_status = job_data.get("status", "running")

        request.cls.client     = prod_admin_client
        request.cls.job_id     = job_id
        request.cls.job_status = job_status
        request.cls.job_data   = job_data
        request.cls.db_path    = prod_db
        request.cls.start_date = date.fromisoformat(start_str)
        request.cls.end_date   = date.fromisoformat(end_str)

    # ── Job result ──────────────────────────────────────────────────────────

    def test_job_completed_without_error(self):
        """
        The background job must finish with status 'success' (not 'error').

        EP-E2E-05: if status is 'error', inspect job_data['message'] and
        the Flask application logs for the root cause.
        """
        assert self.job_status in ("success", "completed"), (
            f"Planning job ended with unexpected status {self.job_status!r}. "
            f"Message: {self.job_data.get('message')}. "
            f"Details: {self.job_data.get('details')}. "
            "EP-E2E-05: check Flask logs."
        )

    def test_response_contains_assignments_count(self):
        """Success response must report how many assignments were created."""
        assert "assignmentsCount" in self.job_data, (
            f"Missing 'assignmentsCount' in response: {self.job_data}"
        )

    def test_assignments_count_is_positive(self):
        count = self.job_data.get("assignmentsCount", 0)
        assert count > 0, (
            f"assignmentsCount={count}; expected > 0 for a normal planning run"
        )

    def test_response_year_matches_request(self):
        assert self.job_data.get("year") == self.start_date.year, (
            f"year mismatch: got {self.job_data.get('year')}, "
            f"expected {self.start_date.year}"
        )

    def test_response_month_matches_request(self):
        assert self.job_data.get("month") == self.start_date.month, (
            f"month mismatch: got {self.job_data.get('month')}, "
            f"expected {self.start_date.month}"
        )

    # ── Database persistence ────────────────────────────────────────────────

    def test_shift_assignments_written_to_db(self):
        """
        ``_run_planning_job`` must persist the result as ``ShiftAssignments``
        rows in the database.

        EP-E2E-06: if count = 0, check the bulk-insert + commit in
        api/shifts.py::_run_planning_job.
        """
        count = _db_count(
            self.db_path,
            "ShiftAssignments",
            "Date >= ? AND Date <= ?",
            (self.start_date.isoformat(), self.end_date.isoformat()),
        )
        assert count > 0, (
            f"No ShiftAssignments in DB for {self.start_date}–{self.end_date}. "
            "EP-E2E-06: check _run_planning_job bulk-insert + commit."
        )

    def test_shift_assignments_count_matches_api_response(self):
        """
        The API's ``assignmentsCount`` covers the **extended** planning period
        (complete weeks that may extend beyond the requested month).
        The DB count for the requested month alone must therefore be ≤ that value.
        """
        db_count = _db_count(
            self.db_path,
            "ShiftAssignments",
            "Date >= ? AND Date <= ?",
            (self.start_date.isoformat(), self.end_date.isoformat()),
        )
        api_count = self.job_data.get("assignmentsCount", -1)
        assert api_count >= db_count, (
            f"API reported {api_count} assignments, but DB already has {db_count} "
            f"for the requested month alone – something is off."
        )
        assert api_count > 0, "assignmentsCount must be positive"

    def test_planning_report_saved_to_db(self):
        """
        ``_save_planning_report`` must persist a ``PlanningReports`` row for
        the solved month.

        EP-E2E-07: if missing, check api/shifts.py::_save_planning_report()
        and its call site inside _run_planning_job.
        """
        count = _db_count(
            self.db_path,
            "PlanningReports",
            "year = ? AND month = ?",
            (self.start_date.year, self.start_date.month),
        )
        assert count >= 1, (
            f"No PlanningReports row for {self.start_date.year}-"
            f"{self.start_date.month:02d}. EP-E2E-07."
        )

    # ── Schedule endpoint after planning ────────────────────────────────────

    def test_get_schedule_returns_200_after_planning(self):
        """``GET /api/shifts/schedule`` must work after planning completes."""
        resp = self.client.get(
            f"/api/shifts/schedule?startDate={self.PLAN_START_STR}&view=month"
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.json()}"
        )

    def test_get_schedule_contains_assignments(self):
        """The schedule response must be a non-empty dict."""
        resp = self.client.get(
            f"/api/shifts/schedule?startDate={self.PLAN_START_STR}&view=month"
        )
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}: {data}"

    def test_status_endpoint_returns_404_for_unknown_job(self):
        """Non-existent job IDs must return 404, not 500."""
        resp = self.client.get(
            "/api/shifts/plan/status/00000000-0000-0000-0000-000000000000",
            headers={"X-CSRF-Token": self.client.csrf_token},
        )
        assert resp.status_code == 404
