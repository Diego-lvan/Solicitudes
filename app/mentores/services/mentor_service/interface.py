"""Abstract :class:`MentorService` — application-facing operations on the catalog.

This is the cross-feature contract consumed by ``solicitudes/intake``. Other
features depend on this interface, never on :class:`MentorRepository`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.schemas import BulkDeactivateResult, MentorPeriodoDTO
from usuarios.schemas import UserDTO


class MentorService(ABC):
    @abstractmethod
    def is_mentor(self, matricula: str) -> bool:
        """Hot path consumed by intake. Returns ``True`` for active mentors only."""

    @abstractmethod
    def list(
        self, *, only_active: bool, page: PageRequest
    ) -> Page[MentorPeriodoDTO]:
        """Paginated catalog list.

        ``only_active=True`` returns one row per currently-open period;
        ``only_active=False`` returns one row per matrícula (the most recent
        period, regardless of status).
        """

    @abstractmethod
    def add(
        self,
        *,
        matricula: str,
        fuente: MentorSource,
        nota: str,
        actor: UserDTO,
    ) -> MentorPeriodoDTO:
        """Manual add or reactivation — opens a new period.

        Raises:
            DomainValidationError: matricula format is invalid.
            MentorAlreadyActive: an open period already exists for ``matricula``.
        """

    @abstractmethod
    def deactivate(self, matricula: str, actor: UserDTO) -> MentorPeriodoDTO:
        """Close the currently-open period for ``matricula``.

        Raises:
            MentorNotFound: no open period exists for ``matricula``.
        """

    @abstractmethod
    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]:
        """Full timeline for ``matricula``, newest period first."""

    @abstractmethod
    def was_mentor_at(self, matricula: str, when: datetime) -> bool:
        """Point-in-time membership check under ``[fecha_alta, fecha_baja)``."""

    @abstractmethod
    def bulk_deactivate(
        self, matriculas: Sequence[str], actor: UserDTO
    ) -> BulkDeactivateResult:
        """Best-effort: close every open period whose matrícula is in input.

        Duplicates in ``matriculas`` are de-duplicated before counting, so
        ``total_attempted`` reflects unique matrículas, not raw input length.
        Matrículas without a currently-open period (already closed, or
        unknown to the catalog) are skipped silently and lumped into
        ``already_inactive`` in the result. No exception is raised when a
        matrícula has no open period — that's the whole point of bulk
        operations.
        """

    @abstractmethod
    def deactivate_all_active(self, actor: UserDTO) -> BulkDeactivateResult:
        """Close every currently-open period in the catalog. Admin-only.

        ``total_attempted == closed`` and ``already_inactive == 0`` for this
        variant since the underlying query targets only open periods.
        """
