"""Maps :class:`AppError` subclasses to the right HTTP response.

In production (DEBUG=False), also catches uncaught non-AppError exceptions and
renders the generic error template with code ``internal_error``. In dev,
non-AppError exceptions are re-raised so Django's debug page can render.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from _shared.exceptions import AppError, AuthenticationRequired, DomainValidationError

logger = logging.getLogger("app.error")


class AppErrorMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self._get_response(request)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        if isinstance(exception, AppError):
            return self._handle_app_error(request, exception)

        # Non-AppError: dev shows Django's debug page; prod renders our generic
        # error template with code "internal_error" and logs the stack trace.
        if settings.DEBUG:
            return None

        logger.error(
            "error.unhandled",
            exc_info=exception,
            extra={
                "path": request.path,
                "user_id": getattr(getattr(request, "user", None), "id", None),
            },
        )

        if _wants_json(request):
            return JsonResponse(
                {"code": "internal_error", "message": "Ocurrió un error interno."},
                status=500,
            )
        return render(
            request,
            "_shared/error.html",
            {
                "code": "internal_error",
                "message": "Ocurrió un error interno.",
                "http_status": 500,
                "request_id": getattr(request, "request_id", None),
            },
            status=500,
        )

    def _handle_app_error(
        self, request: HttpRequest, exception: AppError
    ) -> HttpResponse:
        logger.warning(
            "app_error",
            extra={
                "code": exception.code,
                "path": request.path,
                "user_id": getattr(getattr(request, "user", None), "id", None),
            },
        )

        if isinstance(exception, AuthenticationRequired) and not _wants_json(request):
            # Use Django's documented setting for "where to send anonymous users".
            # JwtAuthenticationMiddleware uses the same name; keeping them aligned.
            login_url = getattr(settings, "LOGIN_URL", "/auth/login/")
            return redirect(login_url)

        if _wants_json(request):
            payload: dict[str, object] = {
                "code": exception.code,
                "message": exception.user_message,
            }
            if isinstance(exception, DomainValidationError):
                payload["field_errors"] = exception.field_errors
            return JsonResponse(payload, status=exception.http_status)

        context = {
            "code": exception.code,
            "message": exception.user_message,
            "http_status": exception.http_status,
            "request_id": getattr(request, "request_id", None),
        }
        return render(request, "_shared/error.html", context, status=exception.http_status)


def _wants_json(request: HttpRequest) -> bool:
    if request.headers.get("HX-Request"):
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept
