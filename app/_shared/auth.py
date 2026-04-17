"""Pure-Python JWT helpers — no Django imports.

Used by the auth middleware introduced in initiative 002.
"""
from __future__ import annotations

import logging
from typing import Any

import jwt
from pydantic import BaseModel

from _shared.exceptions import AuthenticationRequired

logger = logging.getLogger(__name__)


class JwtClaims(BaseModel):
    sub: str
    email: str
    rol: str
    exp: int
    iat: int


def decode_jwt(token: str, *, secret: str, algorithms: list[str]) -> dict[str, Any]:
    """Decode and validate a JWT. Raises :class:`AuthenticationRequired` on failure.

    Library-level error detail is logged server-side, never surfaced to the caller.
    """
    try:
        return jwt.decode(token, secret, algorithms=algorithms)
    except jwt.ExpiredSignatureError as exc:
        logger.info("jwt.expired")
        raise AuthenticationRequired("Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt.invalid: %s", exc)
        raise AuthenticationRequired("Token inválido") from exc


def parse_claims(payload: dict[str, Any]) -> JwtClaims:
    return JwtClaims.model_validate(payload)
