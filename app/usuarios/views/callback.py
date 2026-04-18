"""``GET /auth/callback`` — entry point that consumes the JWT and seats the cookie."""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View

from _shared.auth import decode_jwt, parse_claims
from _shared.exceptions import AuthenticationRequired
from usuarios.constants import SESSION_COOKIE_NAME
from usuarios.dependencies import get_user_service

logger = logging.getLogger(__name__)


class CallbackView(View):
    """Validates the provider's JWT, persists the user, sets the session cookie."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        token = request.GET.get("token", "").strip()
        if not token:
            raise AuthenticationRequired("Token ausente en el callback de autenticación.")

        payload = decode_jwt(
            token, secret=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        claims = parse_claims(payload)

        service = get_user_service()
        service.get_or_create_from_claims(claims)
        # Best-effort SIGA enrichment; SigaUnavailable is swallowed inside the service.
        service.hydrate_from_siga(claims.sub)

        target = _safe_return_url(request.GET.get("return", "/solicitudes/"))
        response = redirect(target)

        max_age = max(0, claims.exp - int(time.time()))
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
            samesite="Lax",
            max_age=max_age,
        )
        return response


def _safe_return_url(raw: str) -> str:
    """Allow only same-host or relative URLs; everything else falls back to /."""
    if not raw:
        return "/"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return raw if raw.startswith("/") else "/"
    if parsed.netloc in settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS:
        return raw
    return "/"
