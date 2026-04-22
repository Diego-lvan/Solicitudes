"""Abstract interface for PlantillaSolicitud persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)


class PlantillaRepository(ABC):
    """Abstract data-access for PlantillaSolicitud."""

    @abstractmethod
    def get_by_id(self, plantilla_id: UUID) -> PlantillaDTO:
        """Return the full plantilla. Raises PlantillaNotFound."""

    @abstractmethod
    def list(self, *, only_active: bool = False) -> list[PlantillaRow]:
        """Return rows for list views, ordered by `nombre`."""

    @abstractmethod
    def create(self, input_dto: CreatePlantillaInput) -> PlantillaDTO:
        """Insert a new plantilla."""

    @abstractmethod
    def update(self, input_dto: UpdatePlantillaInput) -> PlantillaDTO:
        """Replace metadata + body. Raises PlantillaNotFound."""

    @abstractmethod
    def deactivate(self, plantilla_id: UUID) -> None:
        """Set ``activo=False``. Idempotent. Raises PlantillaNotFound."""
