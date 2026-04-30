"""Abstract mentor repository — boundary for ORM access from the service layer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from _shared.pagination import Page, PageRequest
from mentores.schemas import MentorPeriodoDTO, MentorUpsertInput


class UpsertOutcome(StrEnum):
    """Tells the service how an ``add_or_reactivate`` call resolved."""

    INSERTED = "INSERTED"
    REACTIVATED = "REACTIVATED"
    ALREADY_ACTIVE = "ALREADY_ACTIVE"


class MentorRepository(ABC):
    """Persistence boundary for the per-period mentor catalog.

    Implementations must translate Django ORM exceptions into feature-level
    exceptions (``MentorNotFound``); ``Model.DoesNotExist`` must never escape.
    """

    @abstractmethod
    def exists_active(self, matricula: str) -> bool:
        """Hot path consumed by intake — skip DTO marshalling.

        Returns ``True`` iff a period exists with ``fecha_baja IS NULL`` for
        the matrícula. Never raises.
        """

    @abstractmethod
    def get_active_period(self, matricula: str) -> MentorPeriodoDTO:
        """Return the currently-open period for ``matricula``.

        Raises ``MentorNotFound`` if no open period exists.
        """

    @abstractmethod
    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorPeriodoDTO]:
        """Paginated catalog listing.

        - ``only_active=True`` → currently-open periods only
          (``fecha_baja IS NULL``), ordered by ``matricula``.
        - ``only_active=False`` → one row per matrícula (the most-recent
          period), so admins see one entry per person regardless of how
          many historical periods they have. Implementation uses Postgres
          ``DISTINCT ON``.
        """

    @abstractmethod
    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]:
        """All periods for ``matricula``, newest first.

        Returns an empty list if the matrícula has never been a mentor.
        """

    @abstractmethod
    def was_mentor_at(self, matricula: str, when: datetime) -> bool:
        """Point-in-time membership check.

        Returns ``True`` iff a period exists for ``matricula`` whose
        half-open interval ``[fecha_alta, fecha_baja)`` contains ``when``.
        ``fecha_alta`` is inclusive, ``fecha_baja`` is exclusive; an open
        period (``fecha_baja IS NULL``) extends to infinity.
        """

    @abstractmethod
    def add_or_reactivate(
        self, input_dto: MentorUpsertInput
    ) -> tuple[MentorPeriodoDTO, UpsertOutcome]:
        """Open a new period for the matrícula, or no-op if already active.

        Outcomes:
        - ``INSERTED`` — first period for this matrícula.
        - ``REACTIVATED`` — prior periods exist; all closed; new period inserted.
        - ``ALREADY_ACTIVE`` — an open period exists; nothing changed.

        Implementations must recover from a partial-unique-index
        ``IntegrityError`` (concurrent reactivator races) by treating the
        outcome as ``ALREADY_ACTIVE``, never letting it surface as a 500.
        """

    @abstractmethod
    def deactivate(
        self, matricula: str, *, actor_matricula: str
    ) -> MentorPeriodoDTO:
        """Close the currently-open period.

        Stamps ``fecha_baja = now()`` and ``desactivado_por = actor``.
        Raises ``MentorNotFound`` if no open period exists for ``matricula``.
        """

    @abstractmethod
    def deactivate_many(
        self, matriculas: Sequence[str], *, actor_matricula: str
    ) -> int:
        """Bulk-close every currently-open period whose matrícula is in the input.

        Best-effort: matrículas that are already closed (or never existed)
        are skipped silently. Implementations should issue a single bulk
        UPDATE filtered by ``matricula__in`` + ``fecha_baja IS NULL``;
        no per-row read or feature-exception is raised.

        Returns the number of periods actually closed. An empty input
        returns ``0`` without touching the database.
        """

    @abstractmethod
    def deactivate_all_active(self, *, actor_matricula: str) -> int:
        """Bulk-close every currently-open period in the catalog.

        Single bulk UPDATE filtered by ``fecha_baja IS NULL``. Returns the
        number of periods closed. Admin-only; the caller is responsible
        for confirming intent before invoking.
        """
