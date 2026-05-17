"""Pydantic DTOs for the respuesta feature."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from solicitudes.respuesta.constants import MAX_COMENTARIO_CHARS, MAX_FILES_PER_BATCH


class UploadedFile(BaseModel):
    """Carrier for a single file payload as it crosses the view→service seam.

    Not frozen — it holds the raw bytes briefly. The service hashes the
    bytes, persists them via :class:`FileStorage`, and discards this DTO.
    """

    nombre_original: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    content: bytes


class CreateRespuestaInput(BaseModel):
    """Input DTO for ``RespuestaService.create_batch``."""

    folio: str = Field(min_length=1)
    actor_matricula: str = Field(min_length=1)
    actor_role: str = Field(min_length=1)
    comentario: str = Field(default="", max_length=MAX_COMENTARIO_CHARS)
    archivos: list[UploadedFile] = Field(
        default_factory=list, max_length=MAX_FILES_PER_BATCH
    )

    @model_validator(mode="after")
    def _at_least_one_payload(self) -> "CreateRespuestaInput":
        if not self.archivos and not self.comentario.strip():
            raise ValueError("Adjunta al menos un archivo o escribe un comentario.")
        return self


class ArchivoRespuestaDTO(BaseModel):
    """Public surface for a stored response file row."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    respuesta_id: UUID
    nombre_original: str
    content_type: str
    size_bytes: int
    created_at: datetime


class ArchivoRespuestaRecord(BaseModel):
    """Internal record carrying ``stored_path`` + ``sha256`` for the download
    path. Never leaves the feature."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    respuesta_id: UUID
    folio: str
    nombre_original: str
    stored_path: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime

    def to_dto(self) -> ArchivoRespuestaDTO:
        return ArchivoRespuestaDTO(
            id=self.id,
            respuesta_id=self.respuesta_id,
            nombre_original=self.nombre_original,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            created_at=self.created_at,
        )


class RespuestaDTO(BaseModel):
    """Hydrated batch: actor + comentario + ordered files."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    folio: str
    actor_matricula: str
    actor_nombre: str
    actor_role: str
    comentario: str
    created_at: datetime
    archivos: list[ArchivoRespuestaDTO]
