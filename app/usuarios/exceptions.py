"""Feature-level exceptions for the usuarios app.

All inherit (transitively) from :class:`_shared.exceptions.AppError` so they are
mappable to HTTP responses by ``AppErrorMiddleware``.
"""
from __future__ import annotations

from _shared.exceptions import (
    AuthenticationRequired,
    ExternalServiceError,
    NotFound,
    Unauthorized,
)


class InvalidJwt(AuthenticationRequired):
    code = "invalid_jwt"
    user_message = "Tu sesión no es válida. Inicia sesión nuevamente."


class RoleNotRecognized(Unauthorized):
    code = "role_not_recognized"
    user_message = "Tu rol no está autorizado para usar este sistema."


class UserNotFound(NotFound):
    code = "user_not_found"
    user_message = "El usuario no existe."


class SigaUnavailable(ExternalServiceError):
    code = "siga_unavailable"
    user_message = (
        "El sistema de información académica no responde. "
        "Continuamos con datos básicos."
    )
