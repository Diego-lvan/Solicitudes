"""Structured per-request logging."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("request")


class StructuredLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        logger.debug(
            "request.start",
            extra={"method": request.method, "path": request.path},
        )
        response = self._get_response(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request.end",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
