"""Abstract service contract for the plantilla_assets feature."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.plantilla_assets.schemas import (
    CreateAssetInput,
    PlantillaAssetDTO,
    PlantillaAssetRow,
)


class AssetService(ABC):
    @abstractmethod
    def get(self, asset_id: UUID) -> PlantillaAssetDTO:
        """Full DTO or raises AssetNotFound."""

    @abstractmethod
    def list_global(self) -> list[PlantillaAssetRow]:
        """Rows for the global gallery."""

    @abstractmethod
    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetRow]:
        """Rows scoped to a single plantilla."""

    @abstractmethod
    def list_for_render(
        self, plantilla_id: UUID | None
    ) -> list[PlantillaAssetDTO]:
        """DTOs the PDF service uses to build the `assets` render context."""

    @abstractmethod
    def create(self, input_dto: CreateAssetInput) -> PlantillaAssetRow:
        """Validate + persist a new asset; raises domain exceptions on bad input."""

    @abstractmethod
    def delete(self, asset_id: UUID) -> None:
        """Remove an asset and its stored file."""
