"""Abstract interface for TipoSolicitud persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.tipos.schemas import (
    CreateTipoInput,
    TipoSolicitudDTO,
    TipoSolicitudRow,
    UpdateTipoInput,
)
from usuarios.constants import Role


class TipoRepository(ABC):
    """Abstract data-access for TipoSolicitud and its FieldDefinitions."""

    @abstractmethod
    def get_by_id(self, tipo_id: UUID) -> TipoSolicitudDTO:
        """Return the full hydrated tipo. Raises TipoNotFound."""

    @abstractmethod
    def get_by_slug(self, slug: str) -> TipoSolicitudDTO:
        """Return the full hydrated tipo by slug. Raises TipoNotFound."""

    @abstractmethod
    def list(
        self,
        *,
        only_active: bool = False,
        creator_role: Role | None = None,
        responsible_role: Role | None = None,
    ) -> list[TipoSolicitudRow]:
        """Return tipo rows for list views, ordered by `nombre`.

        Filters compose: every supplied filter must match.
        """

    @abstractmethod
    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO:
        """Insert a new tipo and its initial fields. Raises TipoSlugConflict."""

    @abstractmethod
    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO:
        """Replace metadata + fieldset transactionally. Raises TipoNotFound."""

    @abstractmethod
    def deactivate(self, tipo_id: UUID) -> None:
        """Set `activo=False`. Idempotent. Raises TipoNotFound."""

    @abstractmethod
    def has_solicitudes(self, tipo_id: UUID) -> bool:
        """Return True iff at least one solicitud references this tipo.

        Used by the service to gate hard-delete vs. deactivate. Returns False
        until 004 introduces the Solicitud model.
        """
