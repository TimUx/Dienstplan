"""HTTP routes for admin / disponent notifications."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .shared import get_db, require_role, check_csrf

logger = logging.getLogger(__name__)

router = APIRouter()

_NOTIFICATIONS_SELECT = """
                SELECT
                    n.Id, n.Type, n.Severity, n.Title, n.Message,
                    n.ShiftDate, n.ShiftCode, n.RequiredStaff, n.ActualStaff,
                    n.CreatedAt, n.IsRead, n.ReadAt, n.ReadBy,
                    e.Vorname, e.Name,
                    t.Name as TeamName
                FROM AdminNotifications n
                LEFT JOIN Employees e ON n.EmployeeId = e.Id
                LEFT JOIN Teams t ON n.TeamId = t.Id
"""


def _notification_row_to_dict(row: tuple) -> dict:
    """Map notification query row (positional) to API dict."""
    return {
        "id": row[0],
        "type": row[1],
        "severity": row[2],
        "title": row[3],
        "message": row[4],
        "shiftDate": row[5],
        "shiftCode": row[6],
        "requiredStaff": row[7],
        "actualStaff": row[8],
        "createdAt": row[9],
        "isRead": bool(row[10]),
        "readAt": row[11],
        "readBy": row[12],
        "employeeName": f"{row[13]} {row[14]}" if row[13] else None,
        "teamName": row[15],
    }


@router.get("/api/notifications", dependencies=[Depends(require_role("Admin", "Disponent"))])
async def get_notifications(request: Request):
    """Get admin notifications (for Admins and Disponents only)"""
    try:
        unread_only = request.query_params.get("unreadOnly", "false").lower() == "true"
        limit = int(request.query_params.get("limit", 50))

        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()

        unread_clause = "WHERE n.IsRead = 0\n                " if unread_only else ""
        cursor.execute(
            f"""
{_NOTIFICATIONS_SELECT}
                {unread_clause}ORDER BY n.CreatedAt DESC
                LIMIT ?
            """,
            (limit,),
        )

        notifications = [_notification_row_to_dict(row) for row in cursor.fetchall()]
        conn.close()
        return notifications

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Laden der Benachrichtigungen",
            status_code=500,
            exc=e,
            context="get_notifications",
        )


@router.get("/api/notifications/count", dependencies=[Depends(require_role("Admin", "Disponent"))])
async def get_notification_count_endpoint(request: Request):
    """Get count of unread notifications"""
    try:
        db = get_db()
        conn = db.get_connection()
        from notification_manager import get_notification_count

        count = get_notification_count(conn, unread_only=True)
        conn.close()

        return {"count": count}

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Laden der Benachrichtigungsanzahl",
            status_code=500,
            exc=e,
            context="get_notification_count",
        )


@router.post(
    "/api/notifications/{id}/read",
    dependencies=[Depends(require_role("Admin", "Disponent")), Depends(check_csrf)],
)
async def mark_notification_read(request: Request, id: int):
    """Mark notification as read"""
    try:
        db = get_db()
        conn = db.get_connection()
        from notification_manager import mark_notification_as_read

        success = mark_notification_as_read(conn, id, request.session.get("user_email"))
        conn.close()

        if success:
            return {"success": True}
        return JSONResponse(content={"error": "Benachrichtigung nicht gefunden"}, status_code=404)

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Aktualisieren der Benachrichtigung",
            status_code=500,
            exc=e,
            context="mark_notification_read",
        )


@router.post(
    "/api/notifications/mark-all-read",
    dependencies=[Depends(require_role("Admin", "Disponent")), Depends(check_csrf)],
)
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE AdminNotifications
            SET IsRead = 1, ReadAt = CURRENT_TIMESTAMP, ReadBy = ?
            WHERE IsRead = 0
        """,
            (request.session.get("user_email"),),
        )

        conn.commit()
        count = cursor.rowcount
        conn.close()

        return {"success": True, "count": count}

    except Exception as e:
        return api_error(
            logger,
            "Fehler beim Markieren aller Benachrichtigungen",
            status_code=500,
            exc=e,
            context="mark_all_notifications_read",
        )
