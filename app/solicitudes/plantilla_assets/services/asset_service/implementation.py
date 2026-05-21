"""DefaultAssetService — validates uploads, derives slugs, delegates to repository."""
from __future__ import annotations

import io
import logging
from uuid import UUID

from django.conf import settings
from django.utils.text import slugify

from solicitudes.plantilla_assets.constants import (
    ALLOWED_EXT,
    ALLOWED_MIME,
    MAX_ASSET_BYTES,
)
from solicitudes.plantilla_assets.exceptions import (
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
    PlantillaAssetRow,
)
from solicitudes.plantilla_assets.services.asset_service.interface import (
    AssetService,
)

logger = logging.getLogger(__name__)


class DefaultAssetService(AssetService):
    """Concrete asset service.

    Slug derivation: ``slugify(nombre)`` with ``-`` → ``_`` so the slug is
    reachable as ``{{ assets.<slug> }}`` in a Django template. On collision
    within the scope the repository raises ``DuplicateAssetSlug`` (no
    auto-suffix — the admin picks a unique name explicitly).
    """

    def __init__(self, *, asset_repository: AssetRepository) -> None:
        self._repo = asset_repository

    # ---- reads ----

    def get(self, asset_id: UUID) -> PlantillaAssetDTO:
        return self._repo.get(asset_id)

    def list_global(self) -> list[PlantillaAssetRow]:
        return [self._to_row(dto) for dto in self._repo.list_global()]

    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetRow]:
        return [
            self._to_row(dto) for dto in self._repo.list_for_plantilla(plantilla_id)
        ]

    def list_for_render(
        self, plantilla_id: UUID | None
    ) -> list[PlantillaAssetDTO]:
        # Dedup: plantilla-scoped wins over global on the same slug.
        rows = self._repo.list_for_render(plantilla_id)
        seen: dict[str, PlantillaAssetDTO] = {}
        # Iterate plantilla first so it lands in `seen` and globals don't
        # overwrite it.
        for dto in sorted(
            rows, key=lambda d: 0 if d.scope == AssetScope.PLANTILLA else 1
        ):
            seen.setdefault(dto.slug, dto)
        return list(seen.values())

    # ---- writes ----

    def create(self, input_dto: CreateAssetInput) -> PlantillaAssetRow:
        self._validate(input_dto)
        slug = self._derive_slug(input_dto.nombre)
        plantilla_id = (
            input_dto.plantilla_id
            if input_dto.scope == AssetScope.PLANTILLA
            else None
        )
        dto = self._repo.create(
            slug=slug,
            nombre=input_dto.nombre.strip(),
            scope=input_dto.scope.value,
            plantilla_id=plantilla_id,
            file_bytes=input_dto.file_bytes,
            original_filename=input_dto.original_filename,
            mime_type=input_dto.mime_type,
            created_by_id=input_dto.created_by_id,
        )
        logger.info(
            "Asset created",
            extra={"slug": slug, "scope": input_dto.scope.value, "id": str(dto.id)},
        )
        return self._to_row(dto)

    def delete(self, asset_id: UUID) -> None:
        self._repo.delete(asset_id)
        logger.info("Asset deleted", extra={"id": str(asset_id)})

    # ---- helpers ----

    @staticmethod
    def _derive_slug(nombre: str) -> str:
        slug = slugify(nombre).replace("-", "_")
        if not slug:
            # Non-slugifiable name (emoji-only, CJK-only, etc.) would collide
            # to a sentinel and surface a confusing "duplicate slug" later.
            # Reject up front with a clearer message.
            raise InvalidImageType(
                "slug_empty",
                field_errors={
                    "nombre": [
                        "Usa un nombre con al menos una letra o número del alfabeto latino."
                    ]
                },
            )
        return slug

    @staticmethod
    def _validate(input_dto: CreateAssetInput) -> None:
        if len(input_dto.file_bytes) > MAX_ASSET_BYTES:
            raise ImageTooLarge(
                f"size={len(input_dto.file_bytes)} max={MAX_ASSET_BYTES}",
                field_errors={
                    "imagen": [
                        "La imagen pesa más del máximo permitido (2 MB)."
                    ]
                },
            )
        if input_dto.mime_type not in ALLOWED_MIME:
            raise InvalidImageType(
                f"mime={input_dto.mime_type}",
                field_errors={
                    "imagen": ["Formato no permitido. Usa PNG, JPG o WEBP."]
                },
            )
        ext = _ext_of(input_dto.original_filename)
        if ext not in ALLOWED_EXT:
            raise InvalidImageType(
                f"ext={ext}",
                field_errors={
                    "imagen": [
                        "La extensión del archivo no coincide con un formato permitido."
                    ]
                },
            )
        # Content sniff via Pillow — defense in depth against renamed payloads.
        try:
            from PIL import Image, UnidentifiedImageError

            with Image.open(io.BytesIO(input_dto.file_bytes)) as img:
                img.verify()
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
            raise InvalidImageType(
                f"verify failed: {exc}",
                field_errors={
                    "imagen": ["El archivo no parece ser una imagen válida."]
                },
            ) from exc

    @staticmethod
    def _to_row(dto: PlantillaAssetDTO) -> PlantillaAssetRow:
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if not media_url.endswith("/"):
            media_url = f"{media_url}/"
        return PlantillaAssetRow(
            id=dto.id,
            slug=dto.slug,
            nombre=dto.nombre,
            scope=dto.scope,
            plantilla_id=dto.plantilla_id,
            thumb_url=f"{media_url}{dto.file_path}",
            mime_type=dto.mime_type,
            size_bytes=dto.size_bytes,
            created_at=dto.created_at,
        )


def _ext_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
