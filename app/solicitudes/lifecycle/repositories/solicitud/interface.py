"""Solicitud persistence interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import (
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
)


class SolicitudRepository(ABC):
    """Owns Solicitud row reads and writes."""

    @abstractmethod
    def create(
        self,
        *,
        folio: str,
        tipo_id: UUID,
        solicitante_matricula: str,
        estado: Estado,
        form_snapshot: dict[str, Any],
        valores: dict[str, Any],
        requiere_pago: bool,
        pago_exento: bool,
    ) -> SolicitudDetail:
        """Insert a new solicitud and return its hydrated detail."""

    @abstractmethod
    def get_by_folio(self, folio: str) -> SolicitudDetail:
        """Return the solicitud or raise SolicitudNotFound."""

    @abstractmethod
    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        """List the solicitudes filed by ``matricula``."""

    @abstractmethod
    def list_for_responsible_role(
        self,
        responsible_role: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        """List solicitudes whose tipo's ``responsible_role`` matches.

        Used for the personal queue. Admin lookup uses ``list_all`` instead.
        """

    @abstractmethod
    def list_all(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        """List solicitudes regardless of role (admin scope)."""

    @abstractmethod
    def update_estado(self, folio: str, *, new_estado: Estado) -> None:
        """Set the row's estado; updates ``updated_at`` automatically.

        Raises SolicitudNotFound if the row is missing.
        """

    @abstractmethod
    def exists_for_tipo(self, tipo_id: UUID) -> bool:
        """Return True iff at least one solicitud references ``tipo_id``."""
