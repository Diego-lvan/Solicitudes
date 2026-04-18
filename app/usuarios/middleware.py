"""JWT-based authentication middleware.

Replaces Django's :class:`AuthenticationMiddleware`. On every request, looks
for a JWT (cookie ``stk`` first, then ``Authorization: Bearer``), validates it,
upserts the user from claims, and sets both ``request.user`` (an ORM ``User``
for Django's auth contract) and ``request.user_dto`` (a typed DTO).

Anonymous requests are allowed through; views decide whether to require auth.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from _shared.auth import decode_jwt, parse_claims
from _shared.exceptions import AppError, AuthenticationRequired
from usuarios.constants import SESSION_COOKIE_NAME
from usuarios.exceptions import InvalidJwt
from usuarios.models import User
from usuarios.services.user_service import UserService

logger = logging.getLogger(__name__)

# Paths that must never trigger JWT processing:
#   - /health/ : liveness/readiness probes
#   - /static/, /media/ : asset serving
#   - /auth/callback : the handshake endpoint that issues the cookie
SKIP_PREFIXES: tuple[str, ...] = (
    "/health/",
    "/static/",
    "/media/",
    "/auth/callback",
    # Logout must work even with a stale or invalid cookie — never validate.
    "/auth/logout",
    # DEBUG-only dev login: the URL is unmounted in production, but we skip
    # it here too so a stale cookie cannot block reaching the picker page.
    "/auth/dev-login",
)


class JwtAuthenticationMiddleware:
    """Constructor-injected middleware. Django passes ``get_response``;
    the user service is resolved on first use via the factory in
    ``usuarios.dependencies`` so settings are imported lazily.
    """

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
        *,
        user_service_factory: Callable[[], UserService] | None = None,
    ) -> None:
        self._get_response = get_response
        self._user_service_factory = user_service_factory
        self._user_service: UserService | None = None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if _should_skip(request.path, SKIP_PREFIXES):
            request.user = AnonymousUser()
            return self._get_response(request)

        token = _read_token(request)
        if token is None:
            request.user = AnonymousUser()
            return self._get_response(request)

        try:
            payload = decode_jwt(
                token,
                secret=settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            claims = parse_claims(payload)

            service = self._resolve_service()
            user_dto = service.get_or_create_from_claims(claims)
            try:
                orm_user = User.objects.get(pk=user_dto.matricula)
            except User.DoesNotExist as exc:
                # Should never happen — get_or_create_from_claims just upserted
                # the row. If it does, treat as an invalid session.
                logger.error("auth.user_vanished matricula=%s", user_dto.matricula)
                raise InvalidJwt("usuario inexistente tras upsert") from exc
        except AuthenticationRequired:
            # Django's middleware exception conversion does not call our
            # AppErrorMiddleware.process_exception for errors raised here, so
            # we surface the redirect inline. Same intent as AppErrorMiddleware.
            return redirect(settings.LOGIN_URL)
        except AppError:
            # Other AppErrors raised during auth setup must still propagate so
            # AppErrorMiddleware (or, more precisely, Django's exception
            # conversion) returns a 500 page. Tests for those paths exercise
            # the view-level entry points where process_exception runs.
            raise

        request.user = orm_user
        request.user_dto = user_dto  # type: ignore[attr-defined]
        return self._get_response(request)

    def _resolve_service(self) -> UserService:
        if self._user_service is None:
            if self._user_service_factory is None:
                # Local import avoids settings access at module-load time.
                from usuarios.dependencies import get_user_service

                self._user_service_factory = get_user_service
            self._user_service = self._user_service_factory()
        return self._user_service


def _should_skip(path: str, prefixes: Iterable[str]) -> bool:
    return any(path.startswith(p) for p in prefixes)


def _read_token(request: HttpRequest) -> str | None:
    cookie = request.COOKIES.get(SESSION_COOKIE_NAME)
    if cookie:
        return cookie
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer ") :].strip() or None
    return None
