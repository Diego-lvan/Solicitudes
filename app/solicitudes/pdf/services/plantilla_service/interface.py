"""Abstract interface for the PlantillaService."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)


class PlantillaService(ABC):
    """Business logic for the PlantillaSolicitud catalog (admin only)."""

    @abstractmethod
    def list(self, *, only_active: bool = False) -> list[PlantillaRow]: ...

    @abstractmethod
    def get(self, plantilla_id: UUID) -> PlantillaDTO: ...

    @abstractmethod
    def create(self, input_dto: CreatePlantillaInput) -> PlantillaDTO:
        """Validate template syntax, then persist."""

    @abstractmethod
    def update(self, input_dto: UpdatePlantillaInput) -> PlantillaDTO:
        """Validate template syntax, then persist."""

    @abstractmethod
    def deactivate(self, plantilla_id: UUID) -> None: ...
