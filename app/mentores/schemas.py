"""Pydantic DTOs for the mentores feature — boundary types between layers."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mentores.constants import MentorSource


class MentorDTO(BaseModel):
    """Frozen DTO returned by repository and service layers."""

    model_config = ConfigDict(frozen=True)

    matricula: str
    activo: bool
    fuente: MentorSource
    nota: str = ""
    fecha_alta: datetime
    fecha_baja: datetime | None = None


class MentorUpsertInput(BaseModel):
    """Input DTO for repository ``upsert``.

    Carries the fields the repository needs to insert a new row OR reactivate
    an existing inactive matricula. The repository layer is responsible for
    setting ``fecha_alta`` (auto) and clearing ``fecha_baja`` on reactivation.
    """

    matricula: str = Field(min_length=1, max_length=20)
    fuente: MentorSource
    nota: str = Field(default="", max_length=200)
    creado_por_matricula: str = Field(min_length=1, max_length=20)


class CsvImportResult(BaseModel):
    """Counts and per-row failures returned by the CSV importer."""

    model_config = ConfigDict(frozen=True)

    total_rows: int
    inserted: int
    reactivated: int
    skipped_duplicates: int
    invalid_rows: list[dict[str, Any]] = Field(default_factory=list)
