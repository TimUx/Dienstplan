"""Smoke tests for static Web UI routes mounted on FastAPI."""

import pytest


@pytest.mark.api
class TestStaticWebUi:
    def test_index_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_app_js_returns_javascript(self, client):
        r = client.get("/js/app.js")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "javascript" in ct or "text/javascript" in ct
