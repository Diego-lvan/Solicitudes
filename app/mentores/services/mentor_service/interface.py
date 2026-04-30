"""Abstract :class:`MentorService` — application-facing operations on the catalog.

This is the cross-feature contract consumed by ``solicitudes/intake``. Other
features depend on this interface, never on :class:`MentorRepository`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.schemas import MentorDTO
from usuarios.schemas import UserDTO


class MentorService(ABC):
    @abstractmethod
    def is_mentor(self, matricula: str) -> bool:
        """Hot path consumed by intake. Returns ``True`` for active mentors only."""

    @abstractmethod
    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorDTO]:
        """Paginated catalog list."""

    @abstractmethod
    def add(
        self,
        *,
        matricula: str,
        fuente: MentorSource,
        nota: str,
        actor: UserDTO,
    ) -> MentorDTO:
        """Manual add or reactivation.

        Raises:
            DomainValidationError: matricula format is invalid.
            MentorAlreadyActive: an active row already exists for ``matricula``.
        """

    @abstractmethod
    def deactivate(self, matricula: str, actor: UserDTO) -> MentorDTO:
        """Soft-delete the matricula. Idempotent on already-inactive rows.

        Raises:
            MentorNotFound: no row exists for ``matricula``.
        """
