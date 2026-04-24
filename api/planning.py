"""
Planning Router: endpoints for retrieving PlanningReport data.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, Response
from datetime import date

from .shared import get_db, require_auth
from .planning_health_config import (
    HEALTH_STAGE1_FAST_SOLVE_SECONDS,
    HEALTH_GREEN_STAGES,
    HEALTH_YELLOW_STAGES,
    HEALTH_RED_STAGES,
)

router = APIRouter()


def _build_stage_metrics_summary(stage_metrics: list) -> dict:
    """
    Build a compact performance summary from stage metrics.
    """
    if not stage_metrics:
        return {
            "has_metrics": False,
            "total_build_seconds": 0.0,
            "total_solve_seconds": 0.0,
            "slowest_stage": None,
            "successful_stage": None,
            "health": {
                "color": "unknown",
                "reason": "Keine Stage-Metriken vorhanden",
            },
        }

    executed = [m for m in stage_metrics if not m.get("skipped")]
    total_build = sum(float(m.get("build_seconds") or 0.0) for m in executed)
    total_solve = sum(float(m.get("solve_seconds") or 0.0) for m in executed)

    slowest_stage = None
    if executed:
        slowest = max(executed, key=lambda m: float(m.get("solve_seconds") or 0.0))
        slowest_stage = {
            "stage": slowest.get("stage"),
            "label": slowest.get("label"),
            "solve_seconds": float(slowest.get("solve_seconds") or 0.0),
        }

    successful_stage = None
    for metric in stage_metrics:
        if metric.get("solved"):
            successful_stage = {
                "stage": metric.get("stage"),
                "label": metric.get("label"),
                "relaxation_level": metric.get("relaxation_level"),
            }
            break

    if successful_stage is None:
        health = {
            "color": "red",
            "reason": "Keine erfolgreiche Solver-Stufe gefunden",
        }
    else:
        solved_stage = successful_stage.get("stage")
        # Heuristik:
        # - green: Lösung in Stage 1 und <= HEALTH_STAGE1_FAST_SOLVE_SECONDS
        # - yellow: Lösung in Stage 1 aber darüber ODER Lösung in Stage 2/3
        # - red: Notfallplan (Stage 4) oder keine erfolgreiche Solver-Stufe
        if solved_stage in HEALTH_GREEN_STAGES:
            if total_solve <= HEALTH_STAGE1_FAST_SOLVE_SECONDS:
                health = {
                    "color": "green",
                    "reason": "Direkt in Stage 1 mit kurzer Solve-Zeit gelöst",
                }
            else:
                health = {
                    "color": "yellow",
                    "reason": "In Stage 1 gelöst, aber mit erhöhter Solve-Zeit",
                }
        elif solved_stage in HEALTH_YELLOW_STAGES:
            health = {
                "color": "yellow",
                "reason": "Nur mit Fallback-Stufe gelöst",
            }
        elif solved_stage in HEALTH_RED_STAGES:
            health = {
                "color": "red",
                "reason": "Nur Notfallplan verfügbar",
            }
        else:
            health = {
                "color": "red",
                "reason": f"Unbekannte erfolgreiche Stage: {solved_stage}",
            }

    return {
        "has_metrics": True,
        "stage_count": len(stage_metrics),
        "executed_stage_count": len(executed),
        "total_build_seconds": round(total_build, 3),
        "total_solve_seconds": round(total_solve, 3),
        "slowest_stage": slowest_stage,
        "successful_stage": successful_stage,
        "health": health,
    }


def _deserialize_report(report_json: str) -> dict:
    """
    Return the stored report_json as a Python dict.

    The JSON was produced by _serialize_planning_report() in api/shifts.py, so all
    date values are already stored as ISO-8601 strings – no further
    conversion is needed for the JSON response.
    """
    import json
    return json.loads(report_json)


@router.get('/api/planning/report/{year}/{month}', dependencies=[Depends(require_auth)])
def get_planning_report(request: Request, year: int, month: int):
    """
    Return the stored PlanningReport for the given year/month as JSON.

    Returns 404 if no report has been saved yet for that month.
    """
    if month < 1 or month > 12:
        return JSONResponse(content={'error': 'Invalid month (must be 1–12)'}, status_code=400)

    db = get_db()
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT report_json FROM PlanningReports WHERE year = ? AND month = ?",
            (year, month)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None:
        return JSONResponse(content={'error': f'No planning report found for {year}/{month:02d}'}, status_code=404)

    report_dict = _deserialize_report(row['report_json'])
    stage_metrics = report_dict.get('stage_metrics', [])
    report_dict['stage_metrics_summary'] = _build_stage_metrics_summary(stage_metrics)
    return report_dict


@router.get('/api/planning/report/{year}/{month}/summary', dependencies=[Depends(require_auth)])
def get_planning_report_summary(request: Request, year: int, month: int):
    """
    Return the text summary of the stored PlanningReport as plain text.

    Returns 404 if no report has been saved yet for that month.
    """
    if month < 1 or month > 12:
        return JSONResponse(content={'error': 'Invalid month (must be 1–12)'}, status_code=400)

    db = get_db()
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT report_json FROM PlanningReports WHERE year = ? AND month = ?",
            (year, month)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None:
        return JSONResponse(content={'error': f'No planning report found for {year}/{month:02d}'}, status_code=404)

    report_dict = _deserialize_report(row['report_json'])

    # Rebuild a PlanningReport object so we can call generate_text_summary()
    from planning_report import (
        PlanningReport, AbsenceInfo, UncoveredShift, RuleViolation, RelaxedConstraint
    )

    def _parse_date(s: str) -> date:
        return date.fromisoformat(s)

    absent_employees = [
        AbsenceInfo(
            employee_name=a['employee_name'],
            absence_type=a['absence_type'],
            start_date=_parse_date(a['start_date']),
            end_date=_parse_date(a['end_date']),
            notes=a.get('notes'),
        )
        for a in report_dict.get('absent_employees', [])
    ]

    uncovered_shifts = [
        UncoveredShift(
            date=_parse_date(u['date']),
            shift_code=u['shift_code'],
            reason=u['reason'],
        )
        for u in report_dict.get('uncovered_shifts', [])
    ]

    rule_violations = [
        RuleViolation(
            rule_id=v['rule_id'],
            description=v['description'],
            severity=v['severity'],
            affected_dates=[_parse_date(d) for d in v.get('affected_dates', [])],
            cause=v['cause'],
            impact=v['impact'],
        )
        for v in report_dict.get('rule_violations', [])
    ]

    relaxed_constraints = [
        RelaxedConstraint(
            constraint_name=rc['constraint_name'],
            reason=rc['reason'],
            description=rc.get('description', ''),
        )
        for rc in report_dict.get('relaxed_constraints', [])
    ]

    period = report_dict['planning_period']
    report = PlanningReport(
        planning_period=(_parse_date(period[0]), _parse_date(period[1])),
        status=report_dict['status'],
        total_employees=report_dict['total_employees'],
        available_employees=report_dict['available_employees'],
        absent_employees=absent_employees,
        shifts_assigned=report_dict.get('shifts_assigned', {}),
        uncovered_shifts=uncovered_shifts,
        rule_violations=rule_violations,
        relaxed_constraints=relaxed_constraints,
        objective_value=report_dict.get('objective_value', 0.0),
        solver_time_seconds=report_dict.get('solver_time_seconds', 0.0),
        penalty_breakdown=report_dict.get('penalty_breakdown', {}),
        stage_metrics=report_dict.get('stage_metrics', []),
    )

    summary = report.generate_text_summary()
    return Response(content=summary, media_type='text/plain; charset=utf-8')
