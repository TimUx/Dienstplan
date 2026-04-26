"""Persistence helpers for asynchronous planning jobs."""

from datetime import datetime, timedelta
from typing import Optional

from .ops_metrics import increment


def cleanup_old_jobs(db) -> None:
    """Remove finished jobs older than 24 hours."""
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    with db.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM PlanningJobs WHERE finished_at IS NOT NULL AND finished_at < ?",
            (cutoff,),
        )
        increment('planning_jobs_cleaned_up', cursor.rowcount or 0)
        conn.commit()


def create_job(db, job_id: str) -> None:
    cleanup_old_jobs(db)
    with db.connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO PlanningJobs (id, status, started_at) VALUES (?, 'running', ?)",
            (job_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
    increment('planning_jobs_started')


def update_job(
    db,
    job_id: str,
    status: str,
    message: Optional[str] = None,
    result_json: Optional[str] = None,
) -> None:
    finished_at = datetime.utcnow().isoformat() if status in ("completed", "error", "cancelled", "success") else None
    with db.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM PlanningJobs WHERE id=?", (job_id,))
        old_row = cursor.fetchone()
        old_status = old_row['status'] if old_row else None
        conn.execute(
            "UPDATE PlanningJobs SET status=?, message=?, finished_at=? WHERE id=?",
            (status, message, finished_at, job_id),
        )
        if result_json is not None:
            conn.execute("UPDATE PlanningJobs SET result_json=? WHERE id=?", (result_json, job_id))
        conn.commit()

    if old_status != status:
        if status in ("completed", "success"):
            increment('planning_jobs_success')
        elif status == "error":
            increment('planning_jobs_error')
        elif status == "cancelled":
            increment('planning_jobs_cancelled')


def get_job(db, job_id: str):
    with db.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PlanningJobs WHERE id=?", (job_id,))
        return cursor.fetchone()
