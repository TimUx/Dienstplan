"""Unit tests for api.error_utils."""

import logging

import pytest
from fastapi.responses import JSONResponse

from api.error_utils import api_error


@pytest.mark.unit
class TestApiError:
    def test_returns_json_response_with_error_body(self):
        log = logging.getLogger("test_api_error")
        resp = api_error(
            log,
            "Nutzerfreundliche Meldung",
            status_code=503,
            exc=None,
            context=None,
        )
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 503
        body = resp.body.decode()
        assert "Nutzerfreundliche Meldung" in body
        assert '"error"' in body

    def test_logs_exception_with_context(self, caplog):
        caplog.set_level(logging.ERROR)
        log = logging.getLogger("test_api_error_exc")

        exc = ValueError("internal detail")
        resp = api_error(
            log,
            "Etwas ist schiefgelaufen",
            status_code=500,
            exc=exc,
            context="save_widget",
        )
        assert resp.status_code == 500
        assert "save_widget" in caplog.text
        assert "internal detail" in caplog.text
