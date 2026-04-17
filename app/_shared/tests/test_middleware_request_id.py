from __future__ import annotations

import logging

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from _shared.logging_config import RequestIDFilter, get_request_id
from _shared.middleware.request_id import HEADER, RequestIDMiddleware


def _ok(_request: object) -> HttpResponse:
    return HttpResponse("ok")


def test_mints_uuid_when_no_header() -> None:
    rf = RequestFactory()
    middleware = RequestIDMiddleware(_ok)
    response = middleware(rf.get("/"))
    rid = response[HEADER]
    assert rid
    assert len(rid) == 32  # uuid4 hex


def test_echoes_valid_incoming_header() -> None:
    rf = RequestFactory()
    middleware = RequestIDMiddleware(_ok)
    response = middleware(rf.get("/", HTTP_X_REQUEST_ID="abcd1234efgh5678"))
    assert response[HEADER] == "abcd1234efgh5678"


def test_rejects_garbage_incoming_header() -> None:
    rf = RequestFactory()
    middleware = RequestIDMiddleware(_ok)
    response = middleware(rf.get("/", HTTP_X_REQUEST_ID="bad value!"))
    assert response[HEADER] != "bad value!"
    assert len(response[HEADER]) == 32


def test_resets_contextvar_after_request() -> None:
    rf = RequestFactory()
    middleware = RequestIDMiddleware(_ok)
    middleware(rf.get("/"))
    assert get_request_id() is None


def test_request_id_filter_attaches_dash_when_unset(caplog: pytest.LogCaptureFixture) -> None:
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="m", args=None, exc_info=None,
    )
    assert RequestIDFilter().filter(record) is True
    assert record.request_id == "-"  # type: ignore[attr-defined]
