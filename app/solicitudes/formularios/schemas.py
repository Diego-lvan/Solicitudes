"""Pydantic DTOs for the formularios feature.

These DTOs describe a *frozen snapshot* of a TipoSolicitud's fieldset at the
moment a solicitud is filed. The intake service in 004 stores `FormSnapshot`
inside the solicitud row so historical solicitudes survive any later edit to
the live tipo.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from solicitudes.tipos.constants import FieldType


class FieldSnapshot(BaseModel):
    """Frozen copy of a FieldDefinition stored inside Solicitud at intake."""

    model_config = {"frozen": True}

    field_id: UUID
    label: str
    field_type: FieldType
    required: bool
    order: int
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = 10
    max_chars: int | None = None
    placeholder: str = ""
    help_text: str = ""


class FormSnapshot(BaseModel):
    """Frozen copy of a TipoSolicitud's fieldset, captured at intake time."""

    model_config = {"frozen": True}

    tipo_id: UUID
    tipo_slug: str
    tipo_nombre: str
    captured_at: datetime
    fields: list[FieldSnapshot]
