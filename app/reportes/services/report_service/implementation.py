"""DefaultReportService — composes lifecycle aggregations into a DashboardData."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import date

from _shared.pagination import Page, PageRequest
from reportes.schemas import (
    CountByEstado,
    CountByMonth,
    CountByTipo,
    DashboardData,
    ReportFilter,
)
from reportes.services.report_service.interface import ReportService
from solicitudes.lifecycle.schemas import SolicitudFilter, SolicitudRow
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)


def _to_solicitud_filter(report_filter: ReportFilter) -> SolicitudFilter:
    """Translate the form-facing ReportFilter into a lifecycle SolicitudFilter."""
    return SolicitudFilter(
        estado=report_filter.estado,
        tipo_id=report_filter.tipo_id,
        responsible_role=report_filter.responsible_role,
        created_from=report_filter.created_from,
        created_to=report_filter.created_to,
    )


def _default_month_window(today: date) -> tuple[date, date]:
    """Last 12 months ending today (inclusive of today's month)."""
    # Anchor at the first day of the month 11 months ago so the window covers
    # 12 calendar months including the current one.
    start_year = today.year
    start_month = today.month - 11
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    return date(start_year, start_month, 1), today


class DefaultReportService(ReportService):
    def __init__(self, *, lifecycle_service: LifecycleService) -> None:
        self._lifecycle = lifecycle_service

    def dashboard(self, *, filter: ReportFilter) -> DashboardData:
        sf = _to_solicitud_filter(filter)
        by_estado_rows = self._lifecycle.aggregate_by_estado(filters=sf)
        by_tipo_rows = self._lifecycle.aggregate_by_tipo(filters=sf)

        # Apply the 12-month default window only when neither bound is set.
        month_filter = sf
        if filter.created_from is None and filter.created_to is None:
            start, end = _default_month_window(date.today())
            month_filter = sf.model_copy(
                update={"created_from": start, "created_to": end}
            )
        by_month_rows = self._lifecycle.aggregate_by_month(filters=month_filter)

        total = sum(r.count for r in by_estado_rows)
        return DashboardData(
            filter=filter,
            total=total,
            by_estado=[
                CountByEstado(estado=r.estado, count=r.count)
                for r in by_estado_rows
            ],
            by_tipo=[
                CountByTipo(
                    tipo_id=r.tipo_id,
                    tipo_nombre=r.tipo_nombre,
                    count=r.count,
                )
                for r in by_tipo_rows
            ],
            by_month=[
                CountByMonth(year=r.year, month=r.month, count=r.count)
                for r in by_month_rows
            ],
        )

    def list_paginated(
        self, *, filter: ReportFilter, page: PageRequest
    ) -> Page[SolicitudRow]:
        return self._lifecycle.list_for_admin(
            page=page, filters=_to_solicitud_filter(filter)
        )

    def iter_for_admin(
        self, *, filter: ReportFilter, chunk_size: int = 500
    ) -> Iterator[SolicitudRow]:
        return self._lifecycle.iter_for_admin(
            filters=_to_solicitud_filter(filter), chunk_size=chunk_size
        )
