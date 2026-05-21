"""Service-layer tests for DefaultAssetService — in-memory fake repo."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from solicitudes.plantilla_assets.constants import MAX_ASSET_BYTES
from solicitudes.plantilla_assets.exceptions import (
    AssetNotFound,
    DuplicateAssetSlug,
    ImageTooLarge,
    InvalidImageType,
)
from solicitudes.plantilla_assets.repositories.asset_repository.interface import (
    AssetRepository,
)
from solicitudes.plantilla_assets.schemas import (
    AssetScope,
    CreateAssetInput,
    PlantillaAssetDTO,
)
from solicitudes.plantilla_assets.services.asset_service import DefaultAssetService
from solicitudes.plantilla_assets.tests.factories import PNG_1X1


class InMemoryAssetRepository(AssetRepository):
    def __init__(self) -> None:
        self.rows: list[PlantillaAssetDTO] = []

    def get(self, asset_id: UUID) -> PlantillaAssetDTO:
        for r in self.rows:
            if r.id == asset_id:
                return r
        raise AssetNotFound(f"asset_id={asset_id}")

    def list_global(self) -> list[PlantillaAssetDTO]:
        return [r for r in self.rows if r.scope == AssetScope.GLOBAL]

    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetDTO]:
        return [
            r
            for r in self.rows
            if r.scope == AssetScope.PLANTILLA and r.plantilla_id == plantilla_id
        ]

    def list_for_render(self, plantilla_id: UUID | None) -> list[PlantillaAssetDTO]:
        if plantilla_id is None:
            return [r for r in self.rows if r.scope == AssetScope.GLOBAL]
        return [
            r
            for r in self.rows
            if r.scope == AssetScope.GLOBAL
            or (r.scope == AssetScope.PLANTILLA and r.plantilla_id == plantilla_id)
        ]

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
        scope_enum = AssetScope(scope)
        for existing in self.rows:
            if existing.slug == slug and existing.scope == scope_enum:
                if scope_enum == AssetScope.GLOBAL or existing.plantilla_id == plantilla_id:
                    raise DuplicateAssetSlug(f"slug={slug} scope={scope}")
        dto = PlantillaAssetDTO(
            id=uuid4(),
            slug=slug,
            nombre=nombre,
            scope=scope_enum,
            plantilla_id=plantilla_id,
            file_path=f"plantilla_assets/2026/05/{slug}.png",
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            created_at=datetime.now(UTC),
            created_by_id=created_by_id,
        )
        self.rows.append(dto)
        return dto

    def delete(self, asset_id: UUID) -> None:
        for i, r in enumerate(self.rows):
            if r.id == asset_id:
                self.rows.pop(i)
                return
        raise AssetNotFound(f"asset_id={asset_id}")


def _create_input(**overrides: object) -> CreateAssetInput:
    defaults: dict[str, object] = {
        "nombre": "Logo UAZ",
        "scope": AssetScope.GLOBAL,
        "plantilla_id": None,
        "file_bytes": PNG_1X1,
        "original_filename": "logo.png",
        "mime_type": "image/png",
        "created_by_id": "ADM1",
    }
    defaults.update(overrides)
    return CreateAssetInput(**defaults)  # type: ignore[arg-type]


def test_create_happy_path_derives_slug_with_underscores() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    row = service.create(_create_input(nombre="Logo  UAZ Oficial"))
    assert row.slug == "logo_uaz_oficial"
    assert row.nombre == "Logo  UAZ Oficial"


def test_create_rejects_oversize_bytes() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    huge = b"\x00" * (MAX_ASSET_BYTES + 1)
    with pytest.raises(ImageTooLarge) as ei:
        service.create(_create_input(file_bytes=huge))
    assert "imagen" in ei.value.field_errors


def test_create_rejects_invalid_mime() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    with pytest.raises(InvalidImageType) as ei:
        service.create(_create_input(mime_type="application/pdf"))
    assert "imagen" in ei.value.field_errors


def test_create_rejects_invalid_extension() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    with pytest.raises(InvalidImageType):
        service.create(_create_input(original_filename="logo.gif"))


def test_create_rejects_corrupt_bytes() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    # Bytes that pass MIME/ext but Pillow can't decode.
    with pytest.raises(InvalidImageType):
        service.create(_create_input(file_bytes=b"not a png at all"))


def test_list_for_render_dedups_plantilla_wins_over_global() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    plantilla_id = uuid4()
    g = PlantillaAssetDTO(
        id=uuid4(),
        slug="logo",
        nombre="Global Logo",
        scope=AssetScope.GLOBAL,
        plantilla_id=None,
        file_path="x/g.png",
        mime_type="image/png",
        size_bytes=10,
        created_at=datetime.now(UTC),
        created_by_id="ADM1",
    )
    p = PlantillaAssetDTO(
        id=uuid4(),
        slug="logo",
        nombre="Plantilla Logo",
        scope=AssetScope.PLANTILLA,
        plantilla_id=plantilla_id,
        file_path="x/p.png",
        mime_type="image/png",
        size_bytes=10,
        created_at=datetime.now(UTC),
        created_by_id="ADM1",
    )
    repo.rows.extend([g, p])

    result = service.list_for_render(plantilla_id)
    assert len(result) == 1
    assert result[0].id == p.id


def test_delete_delegates_to_repo() -> None:
    repo = InMemoryAssetRepository()
    service = DefaultAssetService(asset_repository=repo)
    row = service.create(_create_input(nombre="Una"))
    service.delete(row.id)
    assert repo.rows == []
