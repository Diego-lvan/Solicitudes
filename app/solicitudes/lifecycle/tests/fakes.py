"""In-memory fakes for lifecycle service tests."""
from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from typing import Any
from uuid import UUID, uuid4

from _shared.pagination import Page, PageRequest
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.repositories.folio.interface import FolioRepository
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import (
    HistorialEntry,
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
)
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class InMemoryFolioRepository(FolioRepository):
    def __init__(self) -> None:
        self._counters: dict[int, int] = {}

    def allocate(self, year: int) -> int:
        self._counters[year] = self._counters.get(year, 0) + 1
        return self._counters[year]


class InMemoryHistorialRepository(HistorialRepository):
    def __init__(self) -> None:
        self._rows: dict[str, list[HistorialEntry]] = {}
        self._ids = count(1)

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
        entry = HistorialEntry(
            id=next(self._ids),
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            actor_matricula=actor_matricula,
            actor_nombre=actor_matricula,
            actor_role=actor_role,
            observaciones=observaciones,
            created_at=datetime.now(tz=UTC),
        )
        self._rows.setdefault(folio, []).append(entry)
        return entry

    def list_for_folio(self, folio: str) -> list[HistorialEntry]:
        return list(self._rows.get(folio, []))


class InMemorySolicitudRepository(SolicitudRepository):
    """Stores rich SolicitudDetail rows keyed by folio."""

    def __init__(
        self, *, historial: InMemoryHistorialRepository | None = None
    ) -> None:
        self._rows: dict[str, SolicitudDetail] = {}
        self._historial = historial or InMemoryHistorialRepository()

    def seed(self, detail: SolicitudDetail) -> None:
        self._rows[detail.folio] = detail

    def create(
        self,
        *,
        folio: str,
        tipo_id: UUID,
        solicitante_matricula: str,
        estado: Estado,
        form_snapshot: dict[str, Any],
        valores: dict[str, Any],
        requiere_pago: bool,
        pago_exento: bool,
    ) -> SolicitudDetail:
        now = datetime.now(tz=UTC)
        detail = SolicitudDetail(
            folio=folio,
            tipo=TipoSolicitudRow(
                id=tipo_id,
                slug=f"tipo-{tipo_id}",
                nombre=f"Tipo {tipo_id}",
                responsible_role=Role.CONTROL_ESCOLAR,
                creator_roles={Role.ALUMNO},
                requires_payment=requiere_pago,
                activo=True,
            ),
            solicitante=UserDTO(
                matricula=solicitante_matricula,
                email=f"{solicitante_matricula}@uaz.edu.mx",
                role=Role.ALUMNO,
            ),
            estado=estado,
            form_snapshot=FormSnapshot.model_validate(form_snapshot),
            valores=valores,
            requiere_pago=requiere_pago,
            pago_exento=pago_exento,
            created_at=now,
            updated_at=now,
            historial=[],
        )
        self._rows[folio] = detail
        return detail

    def get_by_folio(self, folio: str) -> SolicitudDetail:
        if folio not in self._rows:
            raise SolicitudNotFound(f"folio={folio}")
        detail = self._rows[folio]
        return detail.model_copy(
            update={"historial": self._historial.list_for_folio(folio)}
        )

    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        rows = [
            self._row(d)
            for d in self._rows.values()
            if d.solicitante.matricula == matricula
        ]
        return self._paginate(rows, page)

    def list_for_responsible_role(
        self,
        responsible_role: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        rows = [
            self._row(d)
            for d in self._rows.values()
            if d.tipo.responsible_role.value == responsible_role
        ]
        return self._paginate(rows, page)

    def list_all(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        rows = [self._row(d) for d in self._rows.values()]
        return self._paginate(rows, page)

    def update_estado(self, folio: str, *, new_estado: Estado) -> None:
        if folio not in self._rows:
            raise SolicitudNotFound(f"folio={folio}")
        self._rows[folio] = self._rows[folio].model_copy(
            update={"estado": new_estado, "updated_at": datetime.now(tz=UTC)}
        )

    def exists_for_tipo(self, tipo_id: UUID) -> bool:
        return any(d.tipo.id == tipo_id for d in self._rows.values())

    @staticmethod
    def _row(d: SolicitudDetail) -> SolicitudRow:
        return SolicitudRow(
            folio=d.folio,
            tipo_id=d.tipo.id,
            tipo_nombre=d.tipo.nombre,
            solicitante_matricula=d.solicitante.matricula,
            solicitante_nombre=d.solicitante.full_name or d.solicitante.matricula,
            estado=d.estado,
            requiere_pago=d.requiere_pago,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )

    @staticmethod
    def _paginate(rows: list[SolicitudRow], page: PageRequest) -> Page[SolicitudRow]:
        return Page(
            items=rows[page.offset : page.offset + page.page_size],
            total=len(rows),
            page=page.page,
            page_size=page.page_size,
        )


class RecordingNotificationService(NotificationService):
    """Captures notify_* calls so tests can assert on them."""

    def __init__(self) -> None:
        self.creations: list[tuple[str, Role]] = []
        self.transitions: list[tuple[str, Estado, str]] = []

    def notify_creation(self, *, folio: str, responsible_role: Role) -> None:
        self.creations.append((folio, responsible_role))

    def notify_state_change(
        self,
        *,
        folio: str,
        estado_destino: Estado,
        observaciones: str = "",
    ) -> None:
        self.transitions.append((folio, estado_destino, observaciones))


def empty_form_snapshot(tipo_id: UUID | None = None) -> dict[str, Any]:
    return FormSnapshot(
        tipo_id=tipo_id or uuid4(),
        tipo_slug="t",
        tipo_nombre="T",
        captured_at=datetime.now(tz=UTC),
        fields=[],
    ).model_dump(mode="json")
