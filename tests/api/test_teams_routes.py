"""API tests for team list endpoints."""

import pytest


@pytest.mark.api
class TestTeams:
    def test_list_teams_public_or_authenticated(self, client):
        r = client.get("/api/teams")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        assert "id" in first
        assert "name" in first
