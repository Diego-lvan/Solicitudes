"""State machine constants for the solicitud lifecycle.

Estados:
- CREADA      — submitted by the solicitante; awaiting personal review
- EN_PROCESO  — taken by personal in the responsible role; under review
- FINALIZADA  — terminal happy path
- CANCELADA   — terminal cancellation (by solicitante, personal, or admin)

The TRANSITIONS map encodes which (estado, action) pairs are legal. Authorisation
(who is allowed to invoke each action) is layered on top by the service.
"""
from __future__ import annotations

from enum import StrEnum


class Estado(StrEnum):
    CREADA = "CREADA"
    EN_PROCESO = "EN_PROCESO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(m.value, m.display_name) for m in cls]

    @property
    def display_name(self) -> str:
        """User-facing Spanish label for the estado (templates render this)."""
        return _ESTADO_DISPLAY[self]


_ESTADO_DISPLAY: dict[Estado, str] = {
    Estado.CREADA: "Creada",
    Estado.EN_PROCESO: "En proceso",
    Estado.FINALIZADA: "Finalizada",
    Estado.CANCELADA: "Cancelada",
}


# Transition verbs accepted by the lifecycle service. Kept as literal strings
# so view dispatch (`/atender/`, `/finalizar/`, `/cancelar/`) can map URL
# segments to actions without an extra translation table.
ACTION_ATENDER = "atender"
ACTION_FINALIZAR = "finalizar"
ACTION_CANCELAR = "cancelar"

# (estado_actual, accion) -> estado_destino. Any pair not in this map is
# rejected with InvalidStateTransition.
TRANSITIONS: dict[tuple[Estado, str], Estado] = {
    (Estado.CREADA, ACTION_ATENDER): Estado.EN_PROCESO,
    (Estado.EN_PROCESO, ACTION_FINALIZAR): Estado.FINALIZADA,
    (Estado.CREADA, ACTION_CANCELAR): Estado.CANCELADA,
    (Estado.EN_PROCESO, ACTION_CANCELAR): Estado.CANCELADA,
}

TERMINAL: frozenset[Estado] = frozenset({Estado.FINALIZADA, Estado.CANCELADA})
