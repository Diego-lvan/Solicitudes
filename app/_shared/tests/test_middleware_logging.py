from __future__ import annotations

import logging

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from _shared.middleware.logging import StructuredLoggingMiddleware


def _ok(_request: object) -> HttpResponse:
    return HttpResponse("ok", status=201)


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
