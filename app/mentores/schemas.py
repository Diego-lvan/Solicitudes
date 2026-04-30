"""Pydantic DTOs for the mentores feature — boundary types between layers."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mentores.constants import MentorSource


class MentorPeriodoDTO(BaseModel):
    """Frozen DTO for a single mentorship period.

    A matrícula has one DTO per period (alta, baja). ``fecha_baja is None``
    means the period is currently open. ``desactivado_por_matricula`` is set
    when the period was closed by an admin action (legacy backfilled rows
    leave it ``None``; see OQ-012-1 in plan.md).
    """

    model_config = ConfigDict(frozen=True)

    id: int
    matricula: str
    fuente: MentorSource
    nota: str = ""
    fecha_alta: datetime
    fecha_baja: datetime | None = None
    creado_por_matricula: str
    desactivado_por_matricula: str | None = None


class MentorUpsertInput(BaseModel):
    """Input DTO for ``MentorRepository.add_or_reactivate``.

    Carries the fields the repository needs to open a new period for a
    matrícula. The repository stamps ``fecha_alta = timezone.now()``
    explicitly (no ``auto_now_add`` on the model — see model docstring for
    the data-migration rationale).
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


class BulkDeactivateResult(BaseModel):
    """Counts returned by ``MentorService.bulk_deactivate`` /
    ``deactivate_all_active``.

    Field semantics:

    - ``total_attempted`` — number of **unique** matrículas the service was
      asked to act on. The service de-duplicates the input before counting
      so duplicates do not inflate this number (or pollute
      ``already_inactive``).
    - ``closed`` — number of periods this call actually transitioned from
      open to closed.
    - ``already_inactive`` — unique matrículas with no currently-open
      period at the moment of the call. Lumps together two cases the
      catalog cannot distinguish post-hoc: the matrícula was already
      closed before this call, OR the matrícula is unknown to the catalog
      entirely. The flash message surfaces this as "ya estaban inactivos".

    For the "all active" variant, ``total_attempted == closed`` and
    ``already_inactive == 0`` because the query targets only open periods
    by definition.
    """

    model_config = ConfigDict(frozen=True)

    total_attempted: int
    closed: int
    already_inactive: int
