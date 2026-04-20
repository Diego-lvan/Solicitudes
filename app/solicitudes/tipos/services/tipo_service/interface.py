"""Abstract interface for the TipoService."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.tipos.schemas import (
    CreateTipoInput,
    TipoSolicitudDTO,
    TipoSolicitudRow,
    UpdateTipoInput,
)
from usuarios.constants import Role


class TipoService(ABC):
    """Business logic for the TipoSolicitud catalog."""

    @abstractmethod
    def list_for_admin(
        self,
        *,
        only_active: bool = False,
        responsible_role: Role | None = None,
    ) -> list[TipoSolicitudRow]: ...

    @abstractmethod
    def list_for_creator(self, role: Role) -> list[TipoSolicitudRow]: ...

    @abstractmethod
    def get_for_admin(self, tipo_id: UUID) -> TipoSolicitudDTO: ...

    @abstractmethod
    def get_for_creator(self, slug: str, role: Role) -> TipoSolicitudDTO: ...

    @abstractmethod
    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO: ...

    @abstractmethod
    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO: ...

    @abstractmethod
    def deactivate(self, tipo_id: UUID) -> None:
        """Soft-delete (tombstone). The catalog only supports deactivation:
        a tipo with historical solicitudes must remain queryable so each
        per-solicitud ``FormSnapshot`` keeps a `tipo_slug`/`tipo_nombre` for
        listings. Hard-delete is intentionally not part of this surface; if a
        future need surfaces it should land with its own in-use gate via
        ``has_solicitudes``."""

    @abstractmethod
    def snapshot(self, tipo_id: UUID) -> FormSnapshot:
        """Return a frozen FormSnapshot of the tipo's current fieldset."""
