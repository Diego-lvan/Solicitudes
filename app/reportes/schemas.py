"""Pydantic DTOs for the reportes feature — boundary types between layers."""
from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from solicitudes.lifecycle.constants import Estado
from usuarios.constants import Role


class ExportFormat(StrEnum):
    CSV = "csv"
    PDF = "pdf"


class ReportFilter(BaseModel):
    """Form-level filter for the dashboard and exports.

    Translated to ``solicitudes.lifecycle.schemas.SolicitudFilter`` at the
    service boundary; ``reportes`` never imports the lifecycle filter directly
    in its forms or views.
    """

    model_config = ConfigDict(frozen=True)

    estado: Estado | None = None
    tipo_id: UUID | None = None
    responsible_role: Role | None = None
    created_from: date | None = None
    created_to: date | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> ReportFilter:
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from must be on or before created_to")
        return self


class CountByEstado(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: Estado
    count: int


class CountByTipo(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo_id: UUID
    tipo_nombre: str
    count: int


class CountByMonth(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    month: int  # 1..12
    count: int


class DashboardData(BaseModel):
    model_config = ConfigDict(frozen=True)

    filter: ReportFilter
    total: int
    by_estado: list[CountByEstado]
    by_tipo: list[CountByTipo]
    by_month: list[CountByMonth]
