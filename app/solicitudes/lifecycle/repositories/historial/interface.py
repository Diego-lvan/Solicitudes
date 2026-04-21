"""Historial-de-estado repository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import HistorialEntry
from usuarios.constants import Role


class HistorialRepository(ABC):
    """Append-only writer for the solicitud state-transition log."""

    @abstractmethod
    def append(
        self,
        *,
        folio: str,
        estado_anterior: Estado | None,
        estado_nuevo: Estado,
        actor_matricula: str,
        actor_role: Role,
        observaciones: str = "",
    ) -> HistorialEntry:
        """Insert a single historial row and return the hydrated entry."""

    @abstractmethod
    def list_for_folio(self, folio: str) -> list[HistorialEntry]:
        """Return all entries for a folio in chronological order (oldest first)."""
