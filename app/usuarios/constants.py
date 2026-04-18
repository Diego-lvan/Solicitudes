"""Roles and provider-claim mapping for the auth subsystem."""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ALUMNO = "ALUMNO"
    DOCENTE = "DOCENTE"
    CONTROL_ESCOLAR = "CONTROL_ESCOLAR"
    RESPONSABLE_PROGRAMA = "RESPONSABLE_PROGRAMA"
    ADMIN = "ADMIN"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(m.value, m.value.replace("_", " ").title()) for m in cls]


# Provider role claim → internal Role. Isolated here so changes to the provider
# vocabulary do not ripple through the rest of the codebase.
PROVIDER_ROLE_MAP: dict[str, Role] = {
    "alumno": Role.ALUMNO,
    "docente": Role.DOCENTE,
    "control_escolar": Role.CONTROL_ESCOLAR,
    "resp_programa": Role.RESPONSABLE_PROGRAMA,
    "admin": Role.ADMIN,
}


# Cookie name used to carry the JWT after the callback handshake (OQ-002-1).
SESSION_COOKIE_NAME = "stk"
