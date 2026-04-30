"""Abstract mentor repository — boundary for ORM access from the service layer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from _shared.pagination import Page, PageRequest
from mentores.schemas import MentorDTO, MentorUpsertInput


class UpsertOutcome(StrEnum):
    """Tells the service how an ``upsert`` resolved against the existing row."""

    INSERTED = "INSERTED"
    REACTIVATED = "REACTIVATED"
    ALREADY_ACTIVE = "ALREADY_ACTIVE"


class MentorRepository(ABC):
    """Persistence boundary for the mentor catalog.

    Implementations must translate Django ORM exceptions into feature-level
    exceptions (``MentorNotFound``); ``Model.DoesNotExist`` must never escape.
    """

    @abstractmethod
    def get_by_matricula(self, matricula: str) -> MentorDTO:
        """Return the mentor or raise ``MentorNotFound``."""

    @abstractmethod
    def exists_active(self, matricula: str) -> bool:
        """Hot path consumed by intake — skip DTO marshalling.

        Returns ``True`` iff a row exists with ``activo=True``. Never raises.
        """

    @abstractmethod
    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorDTO]:
        """Paginated list ordered by ``matricula``.

        ``only_active=True`` excludes deactivated entries.
        """

    @abstractmethod
    def upsert(self, input_dto: MentorUpsertInput) -> tuple[MentorDTO, UpsertOutcome]:
        """Insert a new row, reactivate an inactive one, or no-op an active one.

        Outcomes:
        - ``INSERTED`` — no prior row existed, a new one was created.
        - ``REACTIVATED`` — an inactive row existed; ``activo`` flipped back
          to ``True``, ``fecha_alta`` reset to ``now``, ``fecha_baja`` cleared.
        - ``ALREADY_ACTIVE`` — an active row already existed; nothing changed.
        """

    @abstractmethod
    def deactivate(self, matricula: str) -> MentorDTO:
        """Soft-delete: set ``activo=False`` and ``fecha_baja=now``.

        Raises ``MentorNotFound`` if no row exists for ``matricula``.
        Idempotent on already-inactive rows: returns the existing DTO unchanged.
        """
