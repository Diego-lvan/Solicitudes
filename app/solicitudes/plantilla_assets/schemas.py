"""Pydantic DTOs for the plantilla_assets feature."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssetScope(StrEnum):
    GLOBAL = "global"
    PLANTILLA = "plantilla"


class PlantillaAssetDTO(BaseModel):
    """Full asset detail; used by the pdf service to resolve `data:` URIs."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    nombre: str
    scope: AssetScope
    plantilla_id: UUID | None
    file_path: str  # storage-relative path, e.g. "plantilla_assets/2026/05/abc.png"
    mime_type: str
    size_bytes: int
    created_at: datetime
    created_by_id: str


class PlantillaAssetRow(BaseModel):
    """Trimmed asset for list views and the editor panel JSON endpoint."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    nombre: str
    scope: AssetScope
    plantilla_id: UUID | None
    thumb_url: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    created_by_label: str = ""


class CreateAssetInput(BaseModel):
    """Input for AssetService.create. file_bytes is validated by the service."""

    nombre: str = Field(min_length=2, max_length=120)
    scope: AssetScope
    plantilla_id: UUID | None = None
    file_bytes: bytes
    original_filename: str
    mime_type: str
    created_by_id: str
