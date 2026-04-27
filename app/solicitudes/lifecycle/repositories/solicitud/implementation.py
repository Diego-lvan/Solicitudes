"""ORM-backed implementation of SolicitudRepository."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

from django.db.models import Count, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import TruncMonth

from _shared.pagination import Page, PageRequest
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import (
    AggregateByEstado,
    AggregateByMonth,
    AggregateByTipo,
    HandlerRef,
    HistorialEntry,
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
)
from solicitudes.models import HistorialEstado, Solicitud
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class OrmSolicitudRepository(SolicitudRepository):
    """Django ORM access to ``Solicitud``. Owns hydrate-with-historial reads."""

    def __init__(self, historial_repository: HistorialRepository) -> None:
        # The detail hydrator needs the historial entries; rather than have
        # callers stitch them together we depend on the historial repo here so
        # ``get_by_folio`` returns a complete `SolicitudDetail`.
        self._historial = historial_repository

    # ---- writes ----

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
        Solicitud.objects.create(
            folio=folio,
            tipo_id=tipo_id,
            solicitante_id=solicitante_matricula,
            estado=estado.value,
            form_snapshot=form_snapshot,
            valores=valores,
            requiere_pago=requiere_pago,
            pago_exento=pago_exento,
        )
        return self.get_by_folio(folio)

    def update_estado(self, folio: str, *, new_estado: Estado) -> None:
        # ``update`` does not call save() so ``auto_now`` will not fire; use
        # ``save(update_fields=...)`` to keep `updated_at` honest.
        try:
            row = Solicitud.objects.get(pk=folio)
        except Solicitud.DoesNotExist as exc:
            raise SolicitudNotFound(f"folio={folio}") from exc
        row.estado = new_estado.value
        row.save(update_fields=["estado", "updated_at"])

    # ---- reads ----

    def get_by_folio(self, folio: str) -> SolicitudDetail:
        try:
            row = (
                Solicitud.objects.select_related("tipo", "solicitante")
                .get(pk=folio)
            )
        except Solicitud.DoesNotExist as exc:
            raise SolicitudNotFound(f"folio={folio}") from exc
        historial = self._historial.list_for_folio(folio)
        return self._to_detail(row, historial)

    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        qs = self._base_queryset().filter(solicitante_id=matricula)
        qs = self._apply_filters(qs, filters)
        return self._paginate(qs, page)

    def list_for_responsible_role(
        self,
        responsible_role: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        qs = self._base_queryset().filter(tipo__responsible_role=responsible_role)
        qs = self._apply_filters(qs, filters)
        return self._paginate(qs, page)

    def list_all(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        qs = self._apply_filters(self._base_queryset(), filters)
        return self._paginate(qs, page)

    def exists_for_tipo(self, tipo_id: UUID) -> bool:
        return Solicitud.objects.filter(tipo_id=tipo_id).exists()

    # ---- helpers ----

    @staticmethod
    def _base_queryset() -> QuerySet[Solicitud]:
        # `select_related` keeps list rendering at 1 query for tipo + solicitante.
        # The Subquery annotations expose the actor of the row's atender
        # transition (CREADA → EN_PROCESO) so queue templates can show
        # "Atendida por" without an N+1 historial lookup. The state machine
        # only allows one such transition, but `order_by("-created_at")` keeps
        # the read deterministic if that ever changes. `iter_for_admin`
        # inherits these columns harmlessly — the subquery is bounded by the
        # existing `(solicitud, -created_at)` index on HistorialEstado.
        atender_qs = HistorialEstado.objects.filter(
            solicitud_id=OuterRef("folio"),
            estado_nuevo=Estado.EN_PROCESO.value,
        ).order_by("-created_at")
        return (
            Solicitud.objects.select_related("tipo", "solicitante")
            .annotate(
                _atendida_por_matricula=Subquery(
                    atender_qs.values("actor__matricula")[:1]
                ),
                _atendida_por_nombre=Subquery(
                    atender_qs.values("actor__full_name")[:1]
                ),
            )
            .order_by("-created_at")
        )

    @staticmethod
    def _apply_filters(
        qs: QuerySet[Solicitud], filters: SolicitudFilter
    ) -> QuerySet[Solicitud]:
        if filters.estado is not None:
            qs = qs.filter(estado=filters.estado.value)
        if filters.tipo_id is not None:
            qs = qs.filter(tipo_id=filters.tipo_id)
        if filters.folio_contains:
            qs = qs.filter(folio__icontains=filters.folio_contains)
        if filters.solicitante_contains:
            term = filters.solicitante_contains
            qs = qs.filter(
                Q(solicitante__matricula__icontains=term)
                | Q(solicitante__full_name__icontains=term)
            )
        if filters.created_from is not None:
            qs = qs.filter(created_at__date__gte=filters.created_from)
        if filters.created_to is not None:
            qs = qs.filter(created_at__date__lte=filters.created_to)
        if filters.responsible_role is not None:
            qs = qs.filter(tipo__responsible_role=filters.responsible_role.value)
        return qs

    # ---- aggregations ----

    def aggregate_by_estado(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByEstado]:
        qs = self._apply_filters(Solicitud.objects.all(), filters)
        rows = (
            qs.values("estado")
            .annotate(count=Count("folio"))
            .order_by("estado")
        )
        return [
            AggregateByEstado(estado=Estado(r["estado"]), count=r["count"])
            for r in rows
        ]

    def aggregate_by_tipo(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByTipo]:
        qs = self._apply_filters(Solicitud.objects.all(), filters)
        rows = (
            qs.values("tipo_id", "tipo__nombre")
            .annotate(count=Count("folio"))
            .order_by("-count", "tipo__nombre")
        )
        return [
            AggregateByTipo(
                tipo_id=r["tipo_id"],
                tipo_nombre=r["tipo__nombre"],
                count=r["count"],
            )
            for r in rows
        ]

    def iter_for_admin(
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ) -> Iterator[SolicitudRow]:
        # On PostgreSQL (prod) `.iterator(chunk_size=...)` opens a server-side
        # cursor and streams. On SQLite (dev) the chunk hint is silently
        # ignored and the full result set is materialised in memory; that's
        # acceptable for dev volumes but worth knowing if you debug a memory
        # spike during a dev-stack export.
        qs = self._apply_filters(self._base_queryset(), filters)
        for row in qs.iterator(chunk_size=chunk_size):
            yield self._to_row(row)

    def aggregate_by_month(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByMonth]:
        qs = self._apply_filters(Solicitud.objects.all(), filters)
        rows = (
            qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("folio"))
            .order_by("month")
        )
        return [
            AggregateByMonth(
                year=r["month"].year,
                month=r["month"].month,
                count=r["count"],
            )
            for r in rows
        ]

    def _paginate(
        self, qs: QuerySet[Solicitud], page: PageRequest
    ) -> Page[SolicitudRow]:
        total = qs.count()
        items = list(qs[page.offset : page.offset + page.page_size])
        return Page(
            items=[self._to_row(r) for r in items],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    @staticmethod
    def _to_row(row: Solicitud) -> SolicitudRow:
        return SolicitudRow(
            folio=row.folio,
            tipo_id=row.tipo_id,
            tipo_nombre=row.tipo.nombre,
            solicitante_matricula=row.solicitante_id,
            solicitante_nombre=row.solicitante.full_name or row.solicitante_id,
            estado=Estado(row.estado),
            requiere_pago=row.requiere_pago,
            pago_exento=row.pago_exento,
            created_at=row.created_at,
            updated_at=row.updated_at,
            atendida_por_matricula=getattr(row, "_atendida_por_matricula", "") or "",
            atendida_por_nombre=getattr(row, "_atendida_por_nombre", "") or "",
        )

    @staticmethod
    def _derive_handler(historial: list[HistorialEntry]) -> HandlerRef | None:
        # The historial is already in memory (loaded by `list_for_folio`); this
        # adds zero SQL. Sort defensively: the ORM repo orders ascending, but
        # callers may pass any order.
        for entry in sorted(historial, key=lambda h: h.created_at, reverse=True):
            if entry.estado_nuevo is Estado.EN_PROCESO:
                return HandlerRef(
                    matricula=entry.actor_matricula,
                    full_name=entry.actor_nombre or entry.actor_matricula,
                    taken_at=entry.created_at,
                )
        return None

    @staticmethod
    def _to_detail(
        row: Solicitud, historial: list[Any]
    ) -> SolicitudDetail:
        tipo = row.tipo
        solicitante = row.solicitante
        return SolicitudDetail(
            folio=row.folio,
            tipo=TipoSolicitudRow(
                id=tipo.id,
                slug=tipo.slug,
                nombre=tipo.nombre,
                responsible_role=Role(tipo.responsible_role),
                creator_roles={Role(r) for r in tipo.creator_roles},
                requires_payment=tipo.requires_payment,
                activo=tipo.activo,
                plantilla_id=tipo.plantilla_id,
            ),
            solicitante=UserDTO(
                matricula=solicitante.matricula,
                email=solicitante.email,
                role=Role(solicitante.role),
                full_name=solicitante.full_name,
                programa=solicitante.programa,
                semestre=solicitante.semestre,
            ),
            estado=Estado(row.estado),
            form_snapshot=FormSnapshot.model_validate(row.form_snapshot),
            valores=dict(row.valores),
            requiere_pago=row.requiere_pago,
            pago_exento=row.pago_exento,
            created_at=row.created_at,
            updated_at=row.updated_at,
            historial=historial,
            atendida_por=OrmSolicitudRepository._derive_handler(historial),
        )
