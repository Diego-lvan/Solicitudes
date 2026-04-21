"""Lifecycle-feature exceptions.

All inherit from `_shared.exceptions` so the global error middleware can map
them to HTTP responses by ``http_status``.
"""
from __future__ import annotations

from _shared.exceptions import Conflict, NotFound
from solicitudes.lifecycle.constants import Estado


class SolicitudNotFound(NotFound):
    code = "solicitud_not_found"
    user_message = "La solicitud no existe."


class InvalidStateTransition(Conflict):
    code = "invalid_state_transition"

    def __init__(self, current: Estado, action: str) -> None:
        super().__init__(f"cannot {action} from {current.value}")
        self.current = current
        self.action = action
        self.user_message = (
            f"No se puede aplicar '{action}' a una solicitud en estado "
            f"{current.value}."
        )


class FolioCollision(Conflict):
    """Reserved for a future allocator strategy.

    The current ``OrmFolioRepository`` uses ``select_for_update`` on a counter
    row, which serialises allocation and cannot produce duplicates. If we ever
    swap to an optimistic strategy (e.g. a Postgres sequence per year that
    might conflict with a hand-inserted folio), the repository should map the
    resulting ``IntegrityError`` to this exception.
    """

    code = "folio_collision"
    user_message = "Conflicto generando folio. Reintenta."
