"""
Planning Blueprint: endpoints for retrieving PlanningReport data.
"""

from flask import Blueprint, jsonify, make_response
from datetime import date

from .shared import get_db, require_auth

bp = Blueprint('planning', __name__)


def _deserialize_report(report_json: str) -> dict:
    """
    Return the stored report_json as a Python dict.

    The JSON was produced by _serialize_planning_report() in api/shifts.py, so all
    date values are already stored as ISO-8601 strings – no further
    conversion is needed for the JSON response.
    """
    import json
    return json.loads(report_json)


@bp.route('/api/planning/report/<int:year>/<int:month>', methods=['GET'])
@require_auth
def get_planning_report(year: int, month: int):
    """
    Return the stored PlanningReport for the given year/month as JSON.

    Returns 404 if no report has been saved yet for that month.
    """
    if month < 1 or month > 12:
        return jsonify({'error': 'Invalid month (must be 1–12)'}), 400

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
        return jsonify({'error': f'No planning report found for {year}/{month:02d}'}), 404

    report_dict = _deserialize_report(row['report_json'])
    return jsonify(report_dict)


@bp.route('/api/planning/report/<int:year>/<int:month>/summary', methods=['GET'])
@require_auth
def get_planning_report_summary(year: int, month: int):
    """
    Return the text summary of the stored PlanningReport as plain text.

    Returns 404 if no report has been saved yet for that month.
    """
    if month < 1 or month > 12:
        return jsonify({'error': 'Invalid month (must be 1–12)'}), 400

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
        return jsonify({'error': f'No planning report found for {year}/{month:02d}'}), 404

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
    )

    summary = report.generate_text_summary()
    response = make_response(summary)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return response
