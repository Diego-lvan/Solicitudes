"""Pydantic DTOs for the archivos feature."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from solicitudes.archivos.constants import ArchivoKind


class ArchivoDTO(BaseModel):
    """Index-row view of a stored file. The bytes themselves are streamed by
    the storage layer; this DTO never carries them."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    solicitud_folio: str
    field_id: UUID | None
    kind: ArchivoKind
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class ArchivoRecord(BaseModel):
    """Internal record carrying everything the service needs to operate on the
    *file*: the storage path plus identity. Authz/validation context for the
    parent solicitud is fetched separately via :class:`LifecycleService` so the
    archivos repo never reaches into another feature's ORM.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    solicitud_folio: str
    field_id: UUID | None
    kind: ArchivoKind
    original_filename: str
    stored_path: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime

    def to_dto(self) -> ArchivoDTO:
        return ArchivoDTO(
            id=self.id,
            solicitud_folio=self.solicitud_folio,
            field_id=self.field_id,
            kind=self.kind,
            original_filename=self.original_filename,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            uploaded_at=self.uploaded_at,
        )
