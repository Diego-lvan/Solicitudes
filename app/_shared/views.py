"""Cross-cutting views used by the project root URL conf."""
from __future__ import annotations

from django.http import HttpRequest, JsonResponse


def health(request: HttpRequest) -> JsonResponse:
    """Liveness probe — returns 200 with the request id from middleware."""
    return JsonResponse(
        {"status": "ok", "request_id": getattr(request, "request_id", None)}
    )
