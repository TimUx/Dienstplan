"""HTTP routes for audit log listing (Admin)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .shared import get_db, require_role
from .statistics_audit import (
    audit_row_to_item,
    build_audit_filters,
    parse_audit_pagination,
)

logger = logging.getLogger(__name__)

router = APIRouter()


_SELECT_AUDIT_COLUMNS = """
            SELECT Id, Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes
            FROM AuditLogs
"""


@router.get("/api/auditlogs", dependencies=[Depends(require_role("Admin"))])
async def get_audit_logs(request: Request):
    """Get audit logs with pagination and filters"""
    try:
        parsed = parse_audit_pagination(request)
        if isinstance(parsed, JSONResponse):
            return parsed
        page, page_size = parsed

        where_clauses, params = build_audit_filters(request)
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()

        count_query = f"SELECT COUNT(*) as total FROM AuditLogs WHERE {where_sql}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        offset = (page - 1) * page_size

        select_query = f"""
{_SELECT_AUDIT_COLUMNS}
            WHERE {where_sql}
            ORDER BY Timestamp DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(select_query, params + [page_size, offset])

        items = [audit_row_to_item(row) for row in cursor.fetchall()]
        conn.close()

        return {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "totalCount": total_count,
            "totalPages": total_pages,
            "hasPreviousPage": page > 1,
            "hasNextPage": page < total_pages,
        }

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Laden der Audit-Logs",
            status_code=500,
            exc=e,
            context="get_audit_logs",
        )


@router.get("/api/auditlogs/recent/{count}", dependencies=[Depends(require_role("Admin"))])
async def get_recent_audit_logs(request: Request, count: int):
    """Get recent audit logs (simplified endpoint for backwards compatibility)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
{_SELECT_AUDIT_COLUMNS}
            ORDER BY Timestamp DESC
            LIMIT ?
        """,
            (count,),
        )

        logs = [audit_row_to_item(row) for row in cursor.fetchall()]
        conn.close()
        return logs

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Laden der Audit-Logs",
            status_code=500,
            exc=e,
            context="get_recent_audit_logs",
        )
