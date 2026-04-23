"""HTTP route for dashboard statistics."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request

from .shared import get_db
from .statistics_dashboard import build_dashboard_payload, default_month_date_range

router = APIRouter()


@router.get("/api/statistics/dashboard")
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics"""
    start_date_str = request.query_params.get("startDate")
    end_date_str = request.query_params.get("endDate")

    if not start_date_str or not end_date_str:
        start_date, end_date = default_month_date_range()
    else:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)

    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        return build_dashboard_payload(cursor, start_date, end_date)
    finally:
        conn.close()
