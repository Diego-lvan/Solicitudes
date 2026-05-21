"""Abstract repository contract for PlantillaAsset persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.plantilla_assets.schemas import (
    CreateAssetInput,
    PlantillaAssetDTO,
)


class AssetRepository(ABC):
    """ORM-free contract over PlantillaAsset rows."""

    @abstractmethod
    def get(self, asset_id: UUID) -> PlantillaAssetDTO:
        """Return the asset DTO or raise AssetNotFound."""

    @abstractmethod
    def list_global(self) -> list[PlantillaAssetDTO]:
        """Return all assets with scope=global, ordered by nombre."""

    @abstractmethod
    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetDTO]:
        """Return all assets with scope=plantilla bound to plantilla_id."""

    @abstractmethod
    def list_for_render(
        self, plantilla_id: UUID | None
    ) -> list[PlantillaAssetDTO]:
        """Return globals + (if plantilla_id) the plantilla's own assets.

        Used by the PDF service to resolve ``{{ assets.<slug> }}`` to data URIs.
        Plantilla-scoped assets take precedence over global assets with the
        same slug.
        """

    @abstractmethod
    def create(
        self,
        *,
        slug: str,
        nombre: str,
        scope: str,
        plantilla_id: UUID | None,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        created_by_id: str,
    ) -> PlantillaAssetDTO:
        """Insert a row and persist the file. Raises DuplicateAssetSlug on collision."""

    @abstractmethod
    def delete(self, asset_id: UUID) -> None:
        """Remove the row and the stored file. Raises AssetNotFound if missing."""
