"""Pydantic DTOs for the solicitud lifecycle feature."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class HistorialEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    estado_anterior: Estado | None
    estado_nuevo: Estado
    actor_matricula: str
    actor_nombre: str
    actor_role: Role
    observaciones: str
    created_at: datetime


class HandlerRef(BaseModel):
    """Personal who performed the atender transition. Empty for never-atendida rows."""

    model_config = ConfigDict(frozen=True)

    matricula: str
    full_name: str
    taken_at: datetime


class SolicitudRow(BaseModel):
    """Row used by list views; thin enough to render a queue or `mis/` table."""

    model_config = ConfigDict(frozen=True)

    folio: str
    tipo_id: UUID
    tipo_nombre: str
    solicitante_matricula: str
    solicitante_nombre: str
    estado: Estado
    requiere_pago: bool
    pago_exento: bool = False
    created_at: datetime
    updated_at: datetime
    atendida_por_matricula: str = ""
    atendida_por_nombre: str = ""


class SolicitudDetail(BaseModel):
    """Hydrated detail view for a single solicitud, including historial."""

    model_config = ConfigDict(frozen=True)

    folio: str
    tipo: TipoSolicitudRow
    solicitante: UserDTO
    estado: Estado
    form_snapshot: FormSnapshot
    valores: dict[str, Any]
    requiere_pago: bool
    pago_exento: bool
    created_at: datetime
    updated_at: datetime
    historial: list[HistorialEntry]
    atendida_por: HandlerRef | None = None


class SolicitudFilter(BaseModel):
    """Filters applied at the repository layer for list views."""

    estado: Estado | None = None
    tipo_id: UUID | None = None
    folio_contains: str | None = None
    # Matches matricula or full_name (case-insensitive, substring).
    solicitante_contains: str | None = None
    created_from: date | None = None
    created_to: date | None = None
    # Filters by the solicitud's tipo.responsible_role; used by reportes/.
    responsible_role: Role | None = None


class AggregateByEstado(BaseModel):
    """Repository-level aggregate row: count of solicitudes per estado."""

    model_config = ConfigDict(frozen=True)

    estado: Estado
    count: int


class AggregateByTipo(BaseModel):
    """Repository-level aggregate row: count of solicitudes per tipo."""

    model_config = ConfigDict(frozen=True)

    tipo_id: UUID
    tipo_nombre: str
    count: int


class AggregateByMonth(BaseModel):
    """Repository-level aggregate row: count of solicitudes per (year, month)."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int  # 1..12
    count: int


class TransitionInput(BaseModel):
    """Service input for any state transition (atender / finalizar / cancelar)."""

    folio: str
    actor_matricula: str
    observaciones: str = Field(default="", max_length=2000)
