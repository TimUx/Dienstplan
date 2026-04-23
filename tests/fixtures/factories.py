"""Small factories for HTTP tests (payloads, query strings)."""

from __future__ import annotations

from datetime import date


def csrf_token(client) -> str:
    return client.get("/api/csrf-token").json()["token"]


def csrf_headers(client: "TestClient", token: str | None = None) -> dict[str, str]:
    tok = token if token is not None else csrf_token(client)
    return {"X-CSRF-Token": tok}


def schedule_url(start: date, view: str | None = None) -> str:
    base = f"/api/shifts/schedule?startDate={start.isoformat()}"
    if view:
        return f"{base}&view={view}"
    return base


def dashboard_url(start: date, end: date) -> str:
    return f"/api/statistics/dashboard?startDate={start.isoformat()}&endDate={end.isoformat()}"


def minimal_employee_payload(suffix: str) -> dict:
    """Payload compatible with POST /api/employees (Admin)."""
    return {
        "vorname": "Factory",
        "name": f"User{suffix}",
        "personalnummer": f"FN{suffix}",
        "email": f"factory.user{suffix}@example.test",
        "password": "TestPass-9a!",
    }
