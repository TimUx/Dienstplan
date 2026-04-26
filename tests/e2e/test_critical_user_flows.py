"""
Fast end-to-end chains over HTTP (no OR-Tools).

These tests document **critical user flows** that must keep working across
refactors: anonymous health, authenticated read of master data, schedule
view, dashboard, logout.

For full production planning (solver + DB writes), see
``tests/integration/test_e2e_production.py`` (marked ``slow`` + ``e2e``).
"""

import pytest

from tests.fixtures import realistic_data as RD
from tests.fixtures.factories import csrf_headers, dashboard_url, schedule_url


pytestmark = pytest.mark.e2e


def test_flow_anonymous_health_then_authenticated_shift_types(client, admin_client):
    h = client.get("/api/health")
    assert h.status_code == 200
    st = admin_client.get("/api/shifttypes")
    assert st.status_code == 200
    codes = {x["code"] for x in st.json()}
    assert {"F", "N", "S"}.issubset(codes)


def test_flow_login_dashboard_schedule_logout(admin_client):
    me = admin_client.get("/api/auth/current-user")
    assert me.status_code == 200

    dash = admin_client.get(
        dashboard_url(RD.SAMPLE_DASHBOARD_FEB_START, RD.SAMPLE_DASHBOARD_FEB_END)
    )
    assert dash.status_code == 200
    body = dash.json()
    assert "employeeWorkHours" in body
    assert "teamWorkload" in body

    sched = admin_client.get(schedule_url(RD.SAMPLE_SCHEDULE_WEEK_MONDAY, view="week"))
    assert sched.status_code == 200

    admin_client.post(
        "/api/auth/logout",
        headers=csrf_headers(admin_client, admin_client.csrf_token),
    )
    assert admin_client.get("/api/auth/current-user").status_code == 401
