"""Async shift planning and plan approval API routes."""

import json
import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .planning_job_store import create_job, get_job, update_job
from .shared import get_db, require_role, validate_monthly_date_range, check_csrf, parse_json_body
from .shifts_planning_core import _run_planning_job
from .shifts_planning_pool import (
    MAX_CONCURRENT_JOBS,
    _active_futures,
    _futures_lock,
    _solver_pool,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post('/api/shifts/plan', dependencies=[Depends(require_role('Admin', 'Disponent')), Depends(check_csrf)])
def plan_shifts(request: Request):
    """
    Start asynchronous shift planning using OR-Tools.

    Returns a job_id immediately; the caller should poll
    GET /api/shifts/plan/status/{job_id} for progress and result.
    """
    start_date_str = request.query_params.get('startDate')
    end_date_str = request.query_params.get('endDate')
    force = request.query_params.get('force', 'false').lower() == 'true'
    if not start_date_str or not end_date_str:
        return JSONResponse(content={'error': 'startDate and endDate are required'}, status_code=400)

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)

        # Validate that planning is for a complete single month
        is_valid, error_msg = validate_monthly_date_range(start_date, end_date)
        if not is_valid:
            return JSONResponse(content={'error': error_msg}, status_code=400)

        # Enforce max concurrent job limit
        with _futures_lock:
            running = sum(1 for f in _active_futures.values() if not f.done())
            if running >= MAX_CONCURRENT_JOBS:
                return JSONResponse(
                    content={'error': f'Maximale Anzahl gleichzeitiger Planungsjobs ({MAX_CONCURRENT_JOBS}) erreicht. Bitte warten Sie, bis ein Job abgeschlossen ist.'},
                    status_code=503
                )

        # Create job entry and submit to process pool
        job_id = str(uuid.uuid4())
        db = get_db()
        create_job(db, job_id)

        future = _solver_pool.submit(
            _run_planning_job,
            job_id, start_date, end_date, force, db.db_path
        )
        with _futures_lock:
            _active_futures[job_id] = future


        return JSONResponse(content={'jobId': job_id, 'status': 'running'}, status_code=202)

    except Exception as e:
        return api_error(
            logger,
            'Planungsjob konnte nicht gestartet werden',
            status_code=500,
            exc=e,
            context='plan_shifts failed',
        )


@router.get('/api/shifts/plan/status/{job_id}', dependencies=[Depends(require_role('Admin', 'Disponent'))])
def get_plan_status(request: Request, job_id: str):
    """
    Poll the status of a background planning job.

    Returns:
        status: 'running' | 'success' | 'error'
        message: human-readable status text
        (on success) assignmentsCount, year, month, extendedPlanning
        (on error)   details, diagnostics
    """
    db = get_db()
    job = get_job(db, job_id)
    if job is None:
        return JSONResponse(content={'error': 'Job not found'}, status_code=404)

    result = {
        'status': job['status'],
        'message': job['message'],
    }
    if job['result_json']:
        try:
            result.update(json.loads(job['result_json']))
        except Exception:
            pass

    if job['started_at']:
        try:
            started = datetime.fromisoformat(job['started_at'])
            elapsed = int((datetime.utcnow() - started).total_seconds())
            result['elapsedSeconds'] = elapsed
        except Exception:
            result['elapsedSeconds'] = 0

    return result


@router.delete('/api/shifts/plan/{job_id}', dependencies=[Depends(require_role('Admin', 'Disponent')), Depends(check_csrf)])

def cancel_plan_job(request: Request, job_id):
    """
    Request cancellation of a background planning job.

    The job is marked as cancelled. Since OR-Tools may not immediately stop,
    this sets the job status to 'cancelled' in the job store.
    """
    db = get_db()
    job = get_job(db, job_id)
    if job is None:
        return JSONResponse(content={'error': 'Job not found'}, status_code=404)
    if job['status'] != 'running':
        return JSONResponse(content={'error': 'Job is not running'}, status_code=400)
    update_job(db, job_id, 'cancelled', 'Planung wurde abgebrochen.')
    return {'success': True, 'message': 'Planung wird abgebrochen.'}


@router.get('/api/shifts/plan/approvals', dependencies=[Depends(require_role('Admin'))])

def get_plan_approvals(request: Request):
    """Get all shift plan approvals (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ShiftPlanApprovals
            ORDER BY Year DESC, Month DESC
        """)
        
        approvals = []
        for row in cursor.fetchall():
            approvals.append({
                'id': row['Id'],
                'year': row['Year'],
                'month': row['Month'],
                'isApproved': bool(row['IsApproved']),
                'approvedAt': row['ApprovedAt'],
                'approvedBy': row['ApprovedBy'],
                'approvedByName': row['ApprovedByName'],
                'notes': row['Notes'],
                'createdAt': row['CreatedAt']
            })
        
        conn.close()
        return approvals
        
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.get('/api/shifts/plan/approvals/{year:int}/{month:int}')

def get_plan_approval_status(request: Request, year, month):
    """Get approval status for a specific month"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ShiftPlanApprovals
            WHERE Year = ? AND Month = ?
        """, (year, month))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {
                'year': year,
                'month': month,
                'isApproved': False,
                'exists': False
            }
        
        return {
            'id': row['Id'],
            'year': row['Year'],
            'month': row['Month'],
            'isApproved': bool(row['IsApproved']),
            'approvedAt': row['ApprovedAt'],
            'approvedBy': row['ApprovedBy'],
            'approvedByName': row['ApprovedByName'],
            'notes': row['Notes'],
            'createdAt': row['CreatedAt'],
            'exists': True
        }
        
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.put('/api/shifts/plan/approvals/{year:int}/{month:int}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])

def approve_plan(request: Request, year, month, data: dict = Depends(parse_json_body)):
    """Approve or unapprove a shift plan for a specific month (Admin only)"""
    try:
        is_approved = data.get('isApproved', True)
        notes = data.get('notes', '')
        
        # Get current user info
        user_id = request.session.get('user_id')
        user_name = request.session.get('user_fullname', 'Unknown Admin')
        
        if not user_id:
            return JSONResponse(content={'error': 'User not authenticated'}, status_code=401)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Update or insert approval record
        if is_approved:
            cursor.execute("""
                INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, ApprovedAt, ApprovedBy, ApprovedByName, Notes, CreatedAt)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(Year, Month) DO UPDATE SET
                    IsApproved = 1,
                    ApprovedAt = ?,
                    ApprovedBy = ?,
                    ApprovedByName = ?,
                    Notes = ?
            """, (year, month, datetime.utcnow().isoformat(), user_id, user_name, notes,
                  datetime.utcnow().isoformat(),
                  datetime.utcnow().isoformat(), user_id, user_name, notes))
        else:
            cursor.execute("""
                INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, CreatedAt)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(Year, Month) DO UPDATE SET
                    IsApproved = 0,
                    ApprovedAt = NULL,
                    ApprovedBy = NULL,
                    ApprovedByName = NULL,
                    Notes = ?
            """, (year, month, datetime.utcnow().isoformat(), notes))
        
        conn.commit()
        conn.close()
        
        action = 'freigegeben' if is_approved else 'Freigabe aufgehoben'
        return {
            'success': True,
            'message': f'Dienstplan für {month:02d}/{year} wurde {action}.'
        }
        
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

