"""ORM-backed implementation of HistorialRepository."""
from __future__ import annotations

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.schemas import HistorialEntry
from solicitudes.models import HistorialEstado
from usuarios.constants import Role


class OrmHistorialRepository(HistorialRepository):
    """Owns access to ``HistorialEstado``. Append-only by contract."""

    def append(
        self,
        *,
        folio: str,
        estado_anterior: Estado | None,
        estado_nuevo: Estado,
        actor_matricula: str,
        actor_role: Role,
        observaciones: str = "",
    ) -> HistorialEntry:
        row = HistorialEstado.objects.create(
            solicitud_id=folio,
            estado_anterior=estado_anterior.value if estado_anterior else None,
            estado_nuevo=estado_nuevo.value,
            actor_id=actor_matricula,
            actor_role=actor_role.value,
            observaciones=observaciones,
        )
        return self._to_dto(row)

    def list_for_folio(self, folio: str) -> list[HistorialEntry]:
        rows = (
            HistorialEstado.objects.filter(solicitud_id=folio)
            .select_related("actor")
            .order_by("created_at", "id")
        )
        return [self._to_dto(r) for r in rows]

    @staticmethod
    def _to_dto(row: HistorialEstado) -> HistorialEntry:
        actor = row.actor
        return HistorialEntry(
            id=row.id,
            estado_anterior=Estado(row.estado_anterior)
            if row.estado_anterior
            else None,
            estado_nuevo=Estado(row.estado_nuevo),
            actor_matricula=actor.matricula,
            actor_nombre=actor.full_name or actor.matricula,
            actor_role=Role(row.actor_role),
            observaciones=row.observaciones,
            created_at=row.created_at,
        )
