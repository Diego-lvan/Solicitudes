"""Pydantic DTOs for the pdf feature."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PlantillaDTO(BaseModel):
    """Persisted plantilla, returned by the repository."""

    model_config = {"frozen": True}

    id: UUID
    nombre: str
    descripcion: str
    html: str
    css: str
    activo: bool


class PlantillaRow(BaseModel):
    """Trimmed DTO for list views — no html/css blobs."""

    model_config = {"frozen": True}

    id: UUID
    nombre: str
    descripcion: str
    activo: bool


class CreatePlantillaInput(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str = ""
    html: str = Field(min_length=1)
    css: str = ""
    activo: bool = True


class UpdatePlantillaInput(CreatePlantillaInput):
    id: UUID


class PdfRenderResult(BaseModel):
    """Output of :class:`PdfService.render_for_solicitud`.

    ``bytes_`` is the rendered PDF payload. Trailing underscore avoids
    shadowing the ``bytes`` builtin in code that destructures the model.
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    folio: str
    bytes_: bytes
    suggested_filename: str
