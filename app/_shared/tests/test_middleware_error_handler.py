from __future__ import annotations

import json

from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from _shared.exceptions import (
    AuthenticationRequired,
    DomainValidationError,
    NotFound,
)
from _shared.middleware.error_handler import AppErrorMiddleware


def _ok(_request: object) -> HttpResponse:
    return HttpResponse("ok")


def test_app_error_renders_html() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    request = rf.get("/things/missing/")
    response = middleware.process_exception(request, NotFound("missing"))
    assert response is not None
    assert response.status_code == 404
    assert b"not_found" in response.content


def test_app_error_returns_json_when_hx_request() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    request = rf.get("/x/", HTTP_HX_REQUEST="true")
    response = middleware.process_exception(request, NotFound())
    assert response is not None
    assert response["Content-Type"].startswith("application/json")
    body = json.loads(response.content)
    assert body["code"] == "not_found"


def test_domain_validation_error_carries_field_errors_in_json() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    request = rf.get("/x/", HTTP_ACCEPT="application/json")
    err = DomainValidationError("bad", field_errors={"name": ["requerido"]})
    response = middleware.process_exception(request, err)
    assert response is not None
    body = json.loads(response.content)
    assert body["field_errors"] == {"name": ["requerido"]}


def test_authentication_required_redirects_to_login() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    response = middleware.process_exception(rf.get("/p/"), AuthenticationRequired())
    assert response is not None
    assert response.status_code == 302


@override_settings(DEBUG=True)
def test_unhandled_exception_is_passed_through_in_dev() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    response = middleware.process_exception(rf.get("/p/"), ValueError("boom"))
    assert response is None


@override_settings(DEBUG=False)
def test_unhandled_exception_renders_internal_error_in_prod() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    response = middleware.process_exception(rf.get("/p/"), ValueError("boom"))
    assert response is not None
    assert response.status_code == 500
    assert b"internal_error" in response.content


@override_settings(DEBUG=False)
def test_unhandled_exception_returns_json_when_requested_in_prod() -> None:
    rf = RequestFactory()
    middleware = AppErrorMiddleware(_ok)
    response = middleware.process_exception(
        rf.get("/p/", HTTP_ACCEPT="application/json"), ValueError("boom")
    )
    assert response is not None
    assert response.status_code == 500
    body = json.loads(response.content)
    assert body["code"] == "internal_error"
