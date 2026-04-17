"""Assigns a request id and exposes it via ``contextvars`` for log records."""
from __future__ import annotations

import re
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from _shared.logging_config import reset_request_id, set_request_id

HEADER = "X-Request-ID"
_VALID_INCOMING = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(HEADER, "")
        rid = incoming if _VALID_INCOMING.match(incoming) else uuid.uuid4().hex
        request.request_id = rid  # type: ignore[attr-defined]
        token = set_request_id(rid)
        try:
            response = self._get_response(request)
        finally:
            reset_request_id(token)
        response[HEADER] = rid
        return response
