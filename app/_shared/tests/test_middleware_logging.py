from __future__ import annotations

import logging

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from _shared.logging_config import build_logging_config
from _shared.middleware.logging import StructuredLoggingMiddleware


def _ok(_request: object) -> HttpResponse:
    return HttpResponse("ok", status=201)


def test_build_logging_config_uses_json_formatter_when_enabled() -> None:
    config = build_logging_config(json_format=True, level="INFO")
    assert (
        config["formatters"]["default"]["()"]
        == "pythonjsonlogger.jsonlogger.JsonFormatter"
    )
    assert config["root"]["level"] == "INFO"


def test_build_logging_config_uses_plain_formatter_by_default() -> None:
    config = build_logging_config(json_format=False, level="DEBUG")
    assert "format" in config["formatters"]["default"]
    assert config["root"]["level"] == "DEBUG"


def test_logs_one_request_end_record(caplog: pytest.LogCaptureFixture) -> None:
    rf = RequestFactory()
    middleware = StructuredLoggingMiddleware(_ok)
    with caplog.at_level(logging.INFO, logger="request"):
        response = middleware(rf.get("/foo"))
    assert response.status_code == 201
    end_records = [r for r in caplog.records if r.message == "request.end"]
    assert len(end_records) == 1
    record = end_records[0]
    assert record.method == "GET"  # type: ignore[attr-defined]
    assert record.path == "/foo"  # type: ignore[attr-defined]
    assert record.status == 201  # type: ignore[attr-defined]
    assert record.duration_ms >= 0  # type: ignore[attr-defined]
