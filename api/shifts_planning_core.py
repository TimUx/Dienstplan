"""Planning job worker: report serialization and subprocess planning entrypoint."""

import json
import logging
from datetime import datetime

from .planning_job_store import get_job, update_job
from .planning_runtime import load_planning_runtime_config

logger = logging.getLogger(__name__)
_runtime_cfg = load_planning_runtime_config()
SOLVER_WORKERS_PER_JOB = _runtime_cfg.solver_workers_per_job

def _serialize_planning_report(report) -> str:
    """
    Serialize a PlanningReport dataclass instance to a JSON string.

    All ``date`` objects are converted to ISO-8601 strings so they round-trip
    safely through the database and the REST API.
    """
    from datetime import date as _date

    def _date_to_str(d) -> str:
        return d.isoformat() if isinstance(d, _date) else d

    data = {
        'planning_period': [
            _date_to_str(report.planning_period[0]),
            _date_to_str(report.planning_period[1]),
        ],
        'status': report.status,
        'total_employees': report.total_employees,
        'available_employees': report.available_employees,
        'absent_employees': [
            {
                'employee_name': a.employee_name,
                'absence_type': a.absence_type,
                'start_date': _date_to_str(a.start_date),
                'end_date': _date_to_str(a.end_date),
                'notes': a.notes,
            }
            for a in report.absent_employees
        ],
        'shifts_assigned': report.shifts_assigned,
        'uncovered_shifts': [
            {
                'date': _date_to_str(u.date),
                'shift_code': u.shift_code,
                'reason': u.reason,
            }
            for u in report.uncovered_shifts
        ],
        'rule_violations': [
            {
                'rule_id': v.rule_id,
                'description': v.description,
                'severity': v.severity,
                'affected_dates': [_date_to_str(d) for d in v.affected_dates],
                'cause': v.cause,
                'impact': v.impact,
            }
            for v in report.rule_violations
        ],
        'relaxed_constraints': [
            {
                'constraint_name': rc.constraint_name,
                'reason': rc.reason,
                'description': rc.description,
            }
            for rc in report.relaxed_constraints
        ],
        'objective_value': report.objective_value,
        'solver_time_seconds': report.solver_time_seconds,
        'penalty_breakdown': report.penalty_breakdown,
        'stage_metrics': report.stage_metrics,
    }
    return json.dumps(data, ensure_ascii=False)


def _save_planning_report(db, year: int, month: int, report) -> None:
    """
    Persist a PlanningReport to the PlanningReports table.

    If a report already exists for the given year/month it is replaced.
    Errors are logged but do not propagate so that a serialization failure
    never prevents the caller from returning a successful response.
    """
    try:
        report_json = _serialize_planning_report(report)
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO PlanningReports (year, month, status, created_at, report_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(year, month) DO UPDATE SET
                    status      = excluded.status,
                    created_at  = excluded.created_at,
                    report_json = excluded.report_json
            """, (year, month, report.status, datetime.utcnow().isoformat(), report_json))
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to save PlanningReport for {year}/{month}: {exc}")


def _run_planning_job(job_id: str, start_date, end_date, force: bool, db_path: str):
    """
    Standalone worker executed in a subprocess via ProcessPoolExecutor.
    Must not reference any FastAPI context objects – all imports are done locally
    and db is accessed directly via Database(db_path).
    """
    import logging as _logging
    import json as _json
    import sqlite3 as _sqlite3
    from datetime import datetime as _datetime, date as _date, timedelta as _timedelta

    _logging.basicConfig(
        level=_logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    _logger = _logging.getLogger(__name__)

    try:
        from api.shared import Database, extend_planning_dates_to_complete_weeks
        db = Database(db_path)

        # Planning steps for progress display (1-based, shown in UI)
        _TOTAL_STEPS = 4

        def _update(status: str, message: str, step: int = None, **kwargs):
            data = {}
            if step is not None:
                data['planningStep'] = step
                data['planningTotalSteps'] = _TOTAL_STEPS
            data.update(kwargs)
            result_json = _json.dumps(data) if data else None
            update_job(db, job_id, status, message, result_json)

        _update('running', 'Daten werden geladen…', step=1)

        # Extend planning dates to complete weeks (may extend into next month)
        extended_start, extended_end = extend_planning_dates_to_complete_weeks(start_date, end_date)
    
        # Log the extension for transparency
        _logger.info(f"Planning for {start_date} to {end_date}")
        if extended_end > end_date:
            _logger.info(f"Extended to complete week: {extended_start} to {extended_end} (added {(extended_end - end_date).days} days from next month)")
        
        # Load data
        from data_loader import load_from_database, load_global_settings
        employees, teams, absences, shift_types = load_from_database(db.db_path)
        
        # Load global settings (consecutive shifts limits, rest time, etc.)
        global_settings = load_global_settings(db.db_path)
        
        # Load existing assignments for the extended period (to lock days from adjacent months)
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get existing assignments for days that extend beyond the current month
        # These will be locked so we don't overwrite already-planned shifts
        locked_team_shift = {}
        locked_employee_weekend = {}
        locked_employee_shift = {}  # NEW: Lock individual employee shifts to prevent double shifts
        
        # Query ALL existing shift assignments in the extended planning period
        # This prevents double shifts when planning across months
        # NOTE: This is separate from the team-level locking below because we need to
        # lock individual employee assignments for the ENTIRE period, not just adjacent months
        cursor.execute("""
            SELECT sa.EmployeeId, sa.Date, st.Code
            FROM ShiftAssignments sa
            INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
            """, (extended_start.isoformat(), extended_end.isoformat()))
            
        existing_employee_assignments = cursor.fetchall()
        
        # Calculate weeks for boundary detection (needed for employee locks)
        # We'll skip locking employee assignments in boundary weeks to avoid conflicts
        from datetime import timedelta
        dates_list = []
        current = extended_start
        while current <= extended_end:
            dates_list.append(current)
            current += timedelta(days=1)
        
        # Calculate weeks
        weeks_for_boundary = []
        current_week = []
        for d in dates_list:
            if d.weekday() == 6 and current_week:  # Sunday
                weeks_for_boundary.append(current_week)
                current_week = []
            current_week.append(d)
        if current_week:
            weeks_for_boundary.append(current_week)
        
        # Identify boundary weeks (same logic as team lock boundary detection)
        boundary_week_dates = set()
        for week_dates in weeks_for_boundary:
            has_dates_before_month = any(d < start_date for d in week_dates)
            has_dates_in_month = any(start_date <= d <= end_date for d in week_dates)
            has_dates_after_month = any(d > end_date for d in week_dates)
            
            # If week spans the boundary, mark all its dates as boundary dates
            if (has_dates_before_month and has_dates_in_month) or (has_dates_in_month and has_dates_after_month):
                boundary_week_dates.update(week_dates)
                logger.info(f"Boundary week detected: {week_dates[0]} to {week_dates[-1]} - employee locks will be skipped")
        
        # Lock existing employee assignments
        # CRITICAL FIX: Skip locking employee assignments in boundary weeks
        # Boundary weeks span month boundaries and may have assignments that conflict
        # with current shift configuration or team-based rotation requirements
        for emp_id, date_str, shift_code in existing_employee_assignments:
            assignment_date = date.fromisoformat(date_str)
            
            # Skip assignments in boundary weeks - they will be re-planned to match current config
            if assignment_date in boundary_week_dates:
                logger.info(f"Skipping lock for Employee {emp_id}, Date {date_str} (in boundary week)")
                continue
            
            # CRITICAL FIX: Convert emp_id to int to match assignment.employee_id type
            # Database returns TEXT ids as strings, but solver uses integers
            try:
                emp_id_int = int(emp_id)
            except (ValueError, TypeError):
                # If conversion fails, use as-is (for backward compatibility with non-numeric IDs)
                emp_id_int = emp_id
            locked_employee_shift[(emp_id_int, assignment_date)] = shift_code
            logger.info(f"Locked: Employee {emp_id_int}, Date {date_str} -> {shift_code} (existing assignment)")
        
        if extended_end > end_date or extended_start < start_date:
            # Query existing shift assignments for extended dates ONLY (not the main month)
            # Join ShiftAssignments with Employees (for TeamId) and ShiftTypes (for Code)
            # Logic: Get assignments within extended range that are OUTSIDE main month range
            # This ensures we only lock assignments from adjacent months, not current month
            cursor.execute("""
                SELECT e.TeamId, sa.Date, st.Code
                FROM ShiftAssignments sa
                INNER JOIN Employees e ON sa.EmployeeId = e.Id
                INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                AND (sa.Date < ? OR sa.Date > ?)
                AND e.TeamId IS NOT NULL
            """, (extended_start.isoformat(), extended_end.isoformat(),
                  start_date.isoformat(), end_date.isoformat()))
            
            existing_team_assignments = cursor.fetchall()
            
            # Build locked constraints from existing assignments
            # We need to map dates to week indices
            from datetime import timedelta
            dates_list = []
            current = extended_start
            while current <= extended_end:
                dates_list.append(current)
                current += timedelta(days=1)
            
            # Calculate weeks
            weeks = []
            current_week = []
            for d in dates_list:
                if d.weekday() == 6 and current_week:  # Sunday
                    weeks.append(current_week)
                    current_week = []
                current_week.append(d)
            if current_week:
                weeks.append(current_week)
            
            # Map dates to week indices
            date_to_week = {}
            for week_idx, week_dates in enumerate(weeks):
                for d in week_dates:
                    date_to_week[d] = week_idx
            
            # Lock existing team assignments
            # CRITICAL FIX: Only lock team shifts for weeks entirely in adjacent months (not current month)
            # Weeks that span the boundary between adjacent and current months should NOT be locked
            # because they may have conflicting shifts (already-planned days vs. to-be-planned days)
            
            # Identify weeks that cross the month boundary
            boundary_weeks = set()
            for week_idx, week_dates in enumerate(weeks):
                # Check if this week contains dates both inside AND outside the main planning month
                has_dates_before_month = any(d < start_date for d in week_dates)
                has_dates_in_month = any(start_date <= d <= end_date for d in week_dates)
                has_dates_after_month = any(d > end_date for d in week_dates)
                
                # If week spans the boundary, don't lock it
                if (has_dates_before_month and has_dates_in_month) or (has_dates_in_month and has_dates_after_month):
                    boundary_weeks.add(week_idx)
                    logger.info(f"Week {week_idx} spans month boundary - will NOT be locked (dates: {week_dates[0]} to {week_dates[-1]})")
            
            # First pass: identify conflicts and boundary weeks
            conflicting_team_weeks = set()  # Track (team_id, week_idx) pairs with conflicts
            for team_id, date_str, shift_code in existing_team_assignments:
                assignment_date = date.fromisoformat(date_str)
                if assignment_date in date_to_week:
                    week_idx = date_to_week[assignment_date]
                    
                    # Skip weeks that cross the month boundary
                    if week_idx in boundary_weeks:
                        continue
                    
                    # Check for conflicts
                    if (team_id, week_idx) in locked_team_shift:
                        existing_shift = locked_team_shift[(team_id, week_idx)]
                        if existing_shift != shift_code:
                            # Conflict detected: different shift codes for same team/week
                            logger.warning(f"CONFLICT: Team {team_id}, Week {week_idx} has conflicting shifts: {existing_shift} vs {shift_code}")
                            conflicting_team_weeks.add((team_id, week_idx))
                    else:
                        # No conflict yet - tentatively add this lock
                        locked_team_shift[(team_id, week_idx)] = shift_code
            
            # Second pass: remove all conflicting locks
            for team_id, week_idx in conflicting_team_weeks:
                if (team_id, week_idx) in locked_team_shift:
                    logger.warning(f"  Removing team lock for Team {team_id}, Week {week_idx} to avoid INFEASIBLE")
                    del locked_team_shift[(team_id, week_idx)]
            
            # Log remaining locks
            for (team_id, week_idx), shift_code in locked_team_shift.items():
                logger.info(f"Locked: Team {team_id}, Week {week_idx} -> {shift_code} (from existing assignments)")
        
        conn.close()
        
        # Load previous shifts for cross-month consecutive days checking
        # CRITICAL FIX: Extended lookback to capture full consecutive chains
        max_consecutive_limit = max((st.max_consecutive_days for st in shift_types), default=7)
        
        # Maximum lookback period to prevent excessive database queries
        max_lookback_days = 60
        
        previous_employee_shifts = {}
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # First pass: Load initial lookback period (same as before)
        initial_lookback_start = extended_start - timedelta(days=max_consecutive_limit)
        initial_lookback_end = extended_start - timedelta(days=1)
        
        cursor.execute("""
            SELECT sa.EmployeeId, sa.Date, st.Code
            FROM ShiftAssignments sa
            INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            WHERE sa.Date >= ? AND sa.Date <= ?
            ORDER BY sa.Date
        """, (initial_lookback_start.isoformat(), initial_lookback_end.isoformat()))
        
        initial_shifts = cursor.fetchall()
        
        # Group shifts by employee for analysis
        employee_shift_dates = {}
        for emp_id, date_str, shift_code in initial_shifts:
            shift_date = date.fromisoformat(date_str)
            try:
                emp_id_int = int(emp_id)
            except (ValueError, TypeError):
                emp_id_int = emp_id
                
            if emp_id_int not in employee_shift_dates:
                employee_shift_dates[emp_id_int] = []
            employee_shift_dates[emp_id_int].append((shift_date, shift_code))
            previous_employee_shifts[(emp_id_int, shift_date)] = shift_code
        
        # Second pass: For each employee with shifts at the start of lookback period,
        # extend lookback to capture their full consecutive chain
        employees_to_extend = []
        for emp_id, shifts in employee_shift_dates.items():
            if not shifts:
                continue
            
            # Sort by date
            shifts.sort(key=lambda x: x[0])
            
            # Check if employee has shifts at the very beginning of lookback period
            # If so, they might have more consecutive days further back
            earliest_shift_date = shifts[0][0]
            
            # Check if there's a consecutive chain leading up to extended_start
            # Work backwards from extended_start - 1 to find consecutive days
            consecutive_days = 0
            check_date = extended_start - timedelta(days=1)
            # Check max_consecutive_limit days to see if all have shifts
            for _ in range(max_consecutive_limit):
                has_shift = any(shift_date == check_date for shift_date, _ in shifts)
                if has_shift:
                    consecutive_days += 1
                    check_date -= timedelta(days=1)
                else:
                    break
            
            # If we found exactly max_consecutive_limit consecutive days without breaking,
            # the chain might extend further back. We need extended lookback to find out.
            if consecutive_days == max_consecutive_limit:
                employees_to_extend.append(emp_id)
        
        # Extend lookback for employees who need it
        if employees_to_extend:
            extended_lookback_start = extended_start - timedelta(days=max_lookback_days)
            extended_lookback_end = initial_lookback_start - timedelta(days=1)
            
            logger.info(f"Extending lookback for {len(employees_to_extend)} employees with long consecutive chains")
            
            # Query extended period for these employees only
            # Use parameterized query to prevent SQL injection
            placeholders = ','.join('?' * len(employees_to_extend))
            query = f"""
                SELECT sa.EmployeeId, sa.Date, st.Code
                FROM ShiftAssignments sa
                INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                AND sa.EmployeeId IN ({placeholders})
                ORDER BY sa.Date
            """
            params = [extended_lookback_start.isoformat(), extended_lookback_end.isoformat()] + employees_to_extend
            cursor.execute(query, params)
            
            for emp_id, date_str, shift_code in cursor.fetchall():
                shift_date = date.fromisoformat(date_str)
                try:
                    emp_id_int = int(emp_id)
                except (ValueError, TypeError):
                    emp_id_int = emp_id
                previous_employee_shifts[(emp_id_int, shift_date)] = shift_code
        
        conn.close()
        
        logger.info(f"Loaded {len(previous_employee_shifts)} previous shift assignments for consecutive days checking")
        if previous_employee_shifts:
            # Find actual date range
            all_dates = [d for (_, d) in previous_employee_shifts.keys()]
            if all_dates:
                actual_lookback_start = min(all_dates)
                actual_lookback_end = max(all_dates)
                logger.info(f"  Previous shifts date range: {actual_lookback_start} to {actual_lookback_end}")
                if employees_to_extend:
                    logger.info(f"  Extended lookback for {len(employees_to_extend)} employees to capture full consecutive chains")
        
        # Create model with extended dates and locked constraints
        _update('running', 'Planungsmodell wird erstellt…', step=2)
        from model import create_shift_planning_model
        from solver import solve_shift_planning, get_infeasibility_diagnostics
        planning_model = create_shift_planning_model(
            employees, teams, extended_start, extended_end, absences, 
            shift_types=shift_types,
            locked_team_shift=locked_team_shift if locked_team_shift else None,
            locked_employee_shift=locked_employee_shift if locked_employee_shift else None,
            previous_employee_shifts=previous_employee_shifts if previous_employee_shifts else None
        )
        
        # Check if cancelled before starting the solve
        row = get_job(db, job_id)
        if row and row['status'] == 'cancelled':
            return

        # Load the previous month's completed shift assignments as warmstart hints.
        # These are passed to the solver via warm_start_shifts so that CP-SAT starts
        # near a known-good solution, reducing time-to-first-feasible by 20–40 %.
        # Only the month directly before start_date is used; older history is ignored.
        warm_start_shifts = {}
        try:
            prev_month_end = start_date - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1)
            conn_ws = db.get_connection()
            cursor_ws = conn_ws.cursor()
            cursor_ws.execute(
                """
                SELECT sa.EmployeeId, sa.Date, st.Code
                FROM ShiftAssignments sa
                INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                WHERE sa.Date >= ? AND sa.Date <= ?
                """,
                (prev_month_start.isoformat(), prev_month_end.isoformat()),
            )
            for emp_id, date_str, shift_code in cursor_ws.fetchall():
                try:
                    emp_id_int = int(emp_id)
                except (ValueError, TypeError):
                    # Employee IDs should always be integers; log if conversion fails
                    # and skip the record to avoid key-type inconsistencies.
                    logger.warning(
                        f"Warmstart: could not convert employee ID {emp_id!r} to int, skipping"
                    )
                    continue
                warm_start_shifts[(emp_id_int, date.fromisoformat(date_str))] = shift_code
            conn_ws.close()
            if warm_start_shifts:
                logger.info(
                    f"Warmstart: loaded {len(warm_start_shifts)} previous-month assignments "
                    f"({prev_month_start} – {prev_month_end}) as solver hints"
                )
        except Exception as _ws_err:
            logger.warning(f"Warmstart hint loading failed (non-critical): {_ws_err}")
            warm_start_shifts = {}

        # Solve
        # SOLVER_TIME_LIMIT_SECONDS can be set in Flask config for test environments.
        # Production leaves it unset (None = unlimited).
        _update('running', 'Optimierung läuft… (dies kann mehrere Minuten dauern)', step=3)

        _constraint_phase_shown = False

        def _solver_progress(event: str, payload: dict):
            nonlocal _constraint_phase_shown
            if event == 'stage_started':
                stage_index = payload.get('stageIndex')
                stage_total = payload.get('totalStages')
                stage_name = payload.get('stageName')
                stage_details = payload.get('stageDetails')
                detail_suffix = f" – {stage_details}" if stage_details else ""
                _update(
                    'running',
                    f"Optimierung läuft… Phase {stage_index}/{stage_total}: {stage_name}{detail_suffix}",
                    step=3,
                    optimizationPhaseIndex=stage_index,
                    optimizationTotalPhases=stage_total,
                    optimizationPhaseLabel=stage_name,
                    optimizationPhaseDetails=stage_details,
                )
                return

            if event == 'constraint':
                if _constraint_phase_shown:
                    return
                _constraint_phase_shown = True
                _update(
                    'running',
                    'Optimierung läuft… Planungsregeln werden vorbereitet',
                    step=3,
                )
                return

            if event == 'solver_search_started':
                _update(
                    'running',
                    'Optimierung läuft… Berechnung wurde gestartet',
                    step=3,
                    optimizationSearchState='started',
                    optimizationSearchPhaseIndex=1,
                    optimizationSearchPhaseTotal=3,
                    optimizationSearchPhaseLabel='Berechnung gestartet',
                )
                return

            if event == 'solver_solution_progress':
                solution_count = payload.get('solutionCount') or 0
                if solution_count == 1:
                    phase_index = 2
                    phase_label = 'Erste Lösung gefunden'
                else:
                    phase_index = 3
                    phase_label = 'Lösung wird weiter verbessert'
                _update(
                    'running',
                    f'Optimierung läuft… {phase_label}',
                    step=3,
                    optimizationSearchState='started',
                    optimizationSearchPhaseIndex=phase_index,
                    optimizationSearchPhaseTotal=3,
                    optimizationSearchPhaseLabel=phase_label,
                )
                return

            if event == 'solver_search_finished':
                _update(
                    'running',
                    'Optimierung läuft… Berechnung abgeschlossen, Ergebnis wird aufbereitet',
                    step=3,
                    optimizationSearchState='finished',
                )
                return

        solver_time_limit = None  # use default
        result = solve_shift_planning(
            planning_model,
            global_settings=global_settings,
            db_path=db.db_path,
            time_limit_seconds=solver_time_limit,
            num_workers=SOLVER_WORKERS_PER_JOB,
            warm_start_shifts=warm_start_shifts if warm_start_shifts else None,
            progress_callback=_solver_progress,
        )
        
        if not result:
            # Get diagnostic information to help user understand the issue
            diagnostics = get_infeasibility_diagnostics(planning_model)
            
            # Build helpful error message with root cause analysis
            error_details = []
            error_details.append(f"Planung für {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')} nicht möglich.")
            error_details.append("")
            error_details.append("GRUNDINFORMATIONEN:")
            error_details.append(f"• Mitarbeiter gesamt: {diagnostics['total_employees']}")
            error_details.append(f"• Teams: {diagnostics['total_teams']}")
            error_details.append(f"• Planungszeitraum: {diagnostics['planning_days']} Tage ({diagnostics['planning_weeks']:.1f} Wochen)")
            
            if diagnostics['employees_with_absences'] > 0:
                error_details.append(f"• Mitarbeiter mit Abwesenheiten: {diagnostics['employees_with_absences']}")
                error_details.append(f"• Abwesenheitstage gesamt: {diagnostics['total_absence_days']} von {diagnostics['total_employees'] * diagnostics['planning_days']} ({diagnostics['absence_ratio']*100:.1f}%)")
            
            # Add specific issues - these are the root causes
            if diagnostics['potential_issues']:
                error_details.append("")
                error_details.append("URSACHEN (Warum die Planung nicht möglich ist):")
                for i, issue in enumerate(diagnostics['potential_issues'], 1):
                    error_details.append(f"{i}. {issue}")
            else:
                error_details.append("")
                error_details.append("URSACHE:")
                error_details.append("Die genaue Ursache konnte nicht automatisch ermittelt werden.")
                error_details.append("Mögliche Gründe:")
                error_details.append("• Zu viele Abwesenheiten im Planungszeitraum")
                error_details.append("• Zu wenige Mitarbeiter für die erforderliche Schichtbesetzung")
                error_details.append("• Konflikte zwischen Ruhezeiten und Schichtzuweisungen")
                error_details.append("• Teams sind zu klein für die Rotationsanforderungen")
            
            # Add staffing analysis for shifts with issues
            problem_shifts = [shift for shift, data in diagnostics['shift_analysis'].items() 
                             if not data['is_feasible']]
            if problem_shifts:
                error_details.append("")
                error_details.append("SCHICHTBESETZUNGSPROBLEME:")
                for shift in problem_shifts:
                    data = diagnostics['shift_analysis'][shift]
                    error_details.append(f"• Schicht {shift}: Nur {data['eligible_employees']} Mitarbeiter verfügbar, aber {data['min_required']} erforderlich")
            
            error_message = "\n".join(error_details)
            
            _update('error',
                    'Planung fehlgeschlagen',
                    details=error_message,
                    diagnostics={
                        'total_employees': diagnostics['total_employees'],
                        'available_employees': diagnostics['available_employees'],
                        'employees_with_absences': diagnostics['employees_with_absences'],
                        'absent_employees': diagnostics['absent_employees'],
                        'potential_issues': diagnostics['potential_issues'],
                        'shift_analysis': diagnostics.get('shift_analysis', {})
                    })
            return
        
        assignments, complete_schedule, planning_report = result
        
        # Filter assignments to include:
        # 1. All days in the requested month (start_date to end_date)
        # 2. Extended days into NEXT month (end_date < date <= extended_end) - to maintain rotation continuity
        # 3. EXCLUDE extended days from PREVIOUS month (extended_start <= date < start_date) - these should already exist
        filtered_assignments = [a for a in assignments if start_date <= a.date <= extended_end]
        
        # Count assignments by category for logging
        current_month_count = len([a for a in filtered_assignments if start_date <= a.date <= end_date])
        future_extended_count = len([a for a in filtered_assignments if a.date > end_date])
        past_excluded_count = len([a for a in assignments if a.date < start_date])
        
        logger.info(f"Total assignments generated: {len(assignments)}")
        logger.info(f"  - Current month ({start_date} to {end_date}): {current_month_count}")
        if future_extended_count > 0:
            logger.info(f"  - Extended into next month ({end_date + timedelta(days=1)} to {extended_end}): {future_extended_count}")
        if past_excluded_count > 0:
            logger.info(f"  - Excluded from previous month (already planned): {past_excluded_count}")
        
        # Save to database
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete existing non-fixed assignments for current month AND future extended days
        # (but NOT for past extended days - those were planned by previous month)
        if force:
            cursor.execute("""
                DELETE FROM ShiftAssignments 
                WHERE Date >= ? AND Date <= ? AND IsFixed = 0
            """, (start_date.isoformat(), extended_end.isoformat()))
        
        # Insert new assignments (current month + future extended days)
        # CRITICAL FIX: Skip assignments that are locked (already exist from previous planning)
        # This prevents duplicate shifts when planning months that overlap with previously planned weeks
        skipped_locked = 0
        inserted = 0
        for assignment in filtered_assignments:
            # Check if this assignment was locked (already exists from previous month)
            if (assignment.employee_id, assignment.date) in locked_employee_shift:
                # Skip inserting - this assignment already exists in the database
                # It was loaded as a locked constraint and should not be duplicated
                skipped_locked += 1
                continue
            
            # CRITICAL: Check if assignment already exists (safety against double shifts)
            # With unique constraint on (EmployeeId, Date), this prevents database errors
            cursor.execute("""
                SELECT Id FROM ShiftAssignments 
                WHERE EmployeeId = ? AND Date = ?
            """, (assignment.employee_id, assignment.date.isoformat()))
            
            if cursor.fetchone():
                # Assignment already exists - skip to prevent duplicate
                skipped_locked += 1
                continue
            
            cursor.execute("""
                INSERT INTO ShiftAssignments 
                (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.employee_id,
                assignment.shift_type_id,
                assignment.date.isoformat(),
                0,
                0,
                datetime.utcnow().isoformat(),
                "Python-OR-Tools"
            ))
            inserted += 1
        
        logger.info(f"Inserted {inserted} new assignments, skipped {skipped_locked} locked assignments")
        
        # TD (Tag Dienst / Day Duty) assignments have been removed from the system
        # This section is no longer used
        
        # Create or update approval record for this month (not approved by default)
        cursor.execute("""
            INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, CreatedAt)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(Year, Month) DO UPDATE SET
                IsApproved = 0,
                ApprovedAt = NULL,
                ApprovedBy = NULL,
                ApprovedByName = NULL
        """, (start_date.year, start_date.month, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()

        # Serialize and persist the PlanningReport so it can be retrieved later
        _update('running', 'Schichten werden gespeichert…', step=4)
        _save_planning_report(db, start_date.year, start_date.month, planning_report)

        report_url = f"/api/planning/report/{start_date.year}/{start_date.month}"

        _update('success',
                f'Erfolgreich! {len(filtered_assignments)} Schichten wurden geplant.',
                assignmentsCount=len(filtered_assignments),
                year=start_date.year,
                month=start_date.month,
                report_url=report_url,
                extendedPlanning={
                    'extendedEnd': extended_end.isoformat() if extended_end > end_date else None,
                    'daysExtended': (extended_end - end_date).days if extended_end > end_date else 0
                })

    except Exception as exc:
        _logger.exception(f"Planning job {job_id} failed")
        _update('error', 'Unbekannter Fehler', details=str(exc))

