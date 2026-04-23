"""Audit log listing: query building and row mapping (shared by paginated + recent endpoints)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


def parse_audit_pagination(request: Request) -> tuple[int, int] | JSONResponse:
    """Return (page, page_size) or a 400 JSONResponse on invalid input."""
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 50))
    except (ValueError, TypeError):
        return JSONResponse(content={"error": "Invalid pagination parameters"}, status_code=400)

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = min(max(page_size, 1), 100)
    return page, page_size


def build_audit_filters(request: Request) -> tuple[list[str], list[Any]]:
    """Static WHERE fragments and parameters (SQL-injection safe)."""
    where_clauses: list[str] = []
    params: list[Any] = []

    entity_name = request.query_params.get("entityName")
    action = request.query_params.get("action")
    start_date = request.query_params.get("startDate")
    end_date = request.query_params.get("endDate")

    if entity_name:
        where_clauses.append("EntityName = ?")
        params.append(entity_name)
    if action:
        where_clauses.append("Action = ?")
        params.append(action)
    if start_date:
        where_clauses.append("DATE(Timestamp) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("DATE(Timestamp) <= ?")
        params.append(end_date)

    return where_clauses, params


def audit_row_to_item(row: Any) -> dict[str, Any]:
    """Normalize one AuditLogs row (sqlite3.Row) to API JSON shape."""
    return {
        "id": row["Id"],
        "timestamp": row["Timestamp"],
        "userId": row["UserId"],
        "userName": row["UserName"],
        "entityName": row["EntityName"],
        "entityId": row["EntityId"],
        "action": row["Action"],
        "changes": row["Changes"],
    }
