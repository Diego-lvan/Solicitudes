"""ORM-backed implementation of AssetRepository."""
from __future__ import annotations

import logging
from uuid import UUID

from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Q

from solicitudes.models import PlantillaAsset
from solicitudes.plantilla_assets.exceptions import (
    AssetNotFound,
    DuplicateAssetSlug,
)
from solicitudes.plantilla_assets.repositories.asset_repository.interface import (
    AssetRepository,
)
from solicitudes.plantilla_assets.schemas import AssetScope, PlantillaAssetDTO

logger = logging.getLogger(__name__)


class OrmAssetRepository(AssetRepository):
    """Django-ORM-backed repository over the ``solicitudes_plantillaasset`` table."""

    def get(self, asset_id: UUID) -> PlantillaAssetDTO:
        try:
            row = PlantillaAsset.objects.get(pk=asset_id)
        except PlantillaAsset.DoesNotExist as exc:
            raise AssetNotFound(f"asset_id={asset_id}") from exc
        return self._to_dto(row)

    def list_global(self) -> list[PlantillaAssetDTO]:
        rows = PlantillaAsset.objects.filter(
            scope=PlantillaAsset.SCOPE_GLOBAL
        ).order_by("nombre")
        return [self._to_dto(row) for row in rows]

    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetDTO]:
        rows = PlantillaAsset.objects.filter(
            scope=PlantillaAsset.SCOPE_PLANTILLA, plantilla_id=plantilla_id
        ).order_by("nombre")
        return [self._to_dto(row) for row in rows]

    def list_for_render(
        self, plantilla_id: UUID | None
    ) -> list[PlantillaAssetDTO]:
        # Plantilla-scoped first so they shadow globals with the same slug
        # when the service deduplicates.
        if plantilla_id is None:
            rows = PlantillaAsset.objects.filter(
                scope=PlantillaAsset.SCOPE_GLOBAL
            ).order_by("nombre")
        else:
            rows = PlantillaAsset.objects.filter(
                Q(scope=PlantillaAsset.SCOPE_GLOBAL)
                | Q(
                    scope=PlantillaAsset.SCOPE_PLANTILLA,
                    plantilla_id=plantilla_id,
                )
            ).order_by("scope", "nombre")
        return [self._to_dto(row) for row in rows]

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
        try:
            row = PlantillaAsset(
                slug=slug,
                nombre=nombre,
                scope=scope,
                plantilla_id=plantilla_id,
                mime_type=mime_type,
                size_bytes=len(file_bytes),
                created_by_id=created_by_id,
            )
            row.imagen.save(original_filename, ContentFile(file_bytes), save=False)
            row.save()
        except IntegrityError as exc:
            # The named constraints land in the message on PostgreSQL; SQLite
            # surfaces a generic "UNIQUE constraint failed:". Match either.
            msg = str(exc).lower()
            is_slug_collision = (
                "unique_global_asset_slug" in msg
                or "unique_plantilla_asset_slug" in msg
                or "unique constraint" in msg
                or "duplicate key" in msg
            )
            if is_slug_collision:
                raise DuplicateAssetSlug(
                    f"slug={slug} scope={scope}"
                ) from exc
            raise
        return self._to_dto(row)

    def delete(self, asset_id: UUID) -> None:
        try:
            row = PlantillaAsset.objects.get(pk=asset_id)
        except PlantillaAsset.DoesNotExist as exc:
            raise AssetNotFound(f"asset_id={asset_id}") from exc
        # Storage cleanup first; if it fails the row stays, surfacing the error.
        try:
            row.imagen.delete(save=False)
        except FileNotFoundError:
            logger.warning("Asset file already missing", extra={"id": str(asset_id)})
        row.delete()

    @staticmethod
    def _to_dto(row: PlantillaAsset) -> PlantillaAssetDTO:
        return PlantillaAssetDTO(
            id=row.id,
            slug=row.slug,
            nombre=row.nombre,
            scope=AssetScope(row.scope),
            plantilla_id=row.plantilla_id,
            file_path=row.imagen.name,
            mime_type=row.mime_type,
            size_bytes=row.size_bytes,
            created_at=row.created_at,
            created_by_id=row.created_by_id,
        )
