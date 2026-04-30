"""Tests for ``DefaultLifecycleService.{aggregate_*, list_for_admin, iter_for_admin}``.

These methods are pass-throughs to the repository, but the interface change
that introduced them is what 009-reports depended on. Pinning a direct test
keeps that contract enforced even if the repo grows a different shape.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import (
    AggregateByEstado,
    AggregateByMonth,
    AggregateByTipo,
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
)
from solicitudes.lifecycle.services.lifecycle_service.implementation import (
    DefaultLifecycleService,
)


class _RecordingRepo(SolicitudRepository):
    """Minimal repo stub that records the args it was called with."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def create(self, **_kwargs: Any) -> SolicitudDetail:  # pragma: no cover
        raise NotImplementedError

    def get_by_folio(self, folio: str) -> SolicitudDetail:  # pragma: no cover
        raise NotImplementedError

    def list_for_solicitante(self, **_kwargs: Any) -> Page[SolicitudRow]:  # pragma: no cover
        raise NotImplementedError

    def list_for_responsible_role(  # pragma: no cover
        self, **_kwargs: Any
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def list_all(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        self.calls.append(("list_all", {"page": page, "filters": filters}))
        return Page(items=[], total=0, page=page.page, page_size=page.page_size)

    def update_estado(self, *_a: Any, **_kw: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists_for_tipo(self, tipo_id: UUID) -> bool:  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_estado(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByEstado]:
        self.calls.append(("aggregate_by_estado", {"filters": filters}))
        return [AggregateByEstado(estado=Estado.CREADA, count=7)]

    def aggregate_by_tipo(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByTipo]:
        self.calls.append(("aggregate_by_tipo", {"filters": filters}))
        return [
            AggregateByTipo(tipo_id=uuid4(), tipo_nombre="Constancia", count=3)
        ]

    def aggregate_by_month(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByMonth]:
        self.calls.append(("aggregate_by_month", {"filters": filters}))
        return [AggregateByMonth(year=2026, month=4, count=2)]

    def iter_for_admin(
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ):
        self.calls.append(
            ("iter_for_admin", {"filters": filters, "chunk_size": chunk_size})
        )
        return iter(())


class _NoopNotifier(NotificationService):
    def notify_creation(self, **_kwargs: Any) -> None:
        return None

    def notify_state_change(self, **_kwargs: Any) -> None:
        return None


@pytest.fixture
def svc_and_repo() -> tuple[DefaultLifecycleService, _RecordingRepo]:
    repo = _RecordingRepo()
    svc = DefaultLifecycleService(
        solicitud_repository=repo,
        historial_repository=None,  # type: ignore[arg-type]  # not exercised here
        notification_service=_NoopNotifier(),
    )
    return svc, repo


def test_aggregate_by_estado_delegates_to_repo(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    f = SolicitudFilter(estado=Estado.CREADA)
    result = svc.aggregate_by_estado(filters=f)
    assert result == [AggregateByEstado(estado=Estado.CREADA, count=7)]
    assert repo.calls == [("aggregate_by_estado", {"filters": f})]


def test_aggregate_by_tipo_delegates_to_repo(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    f = SolicitudFilter()
    result = svc.aggregate_by_tipo(filters=f)
    assert result and result[0].tipo_nombre == "Constancia"
    assert repo.calls == [("aggregate_by_tipo", {"filters": f})]


def test_aggregate_by_month_delegates_to_repo(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    f = SolicitudFilter()
    result = svc.aggregate_by_month(filters=f)
    assert result == [AggregateByMonth(year=2026, month=4, count=2)]
    assert repo.calls == [("aggregate_by_month", {"filters": f})]


def test_list_for_admin_delegates_with_paging(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    f = SolicitudFilter()
    page = PageRequest(page=2, page_size=25)
    result = svc.list_for_admin(page=page, filters=f)
    assert result.total == 0
    assert repo.calls == [("list_all", {"page": page, "filters": f})]


def test_iter_for_admin_passes_chunk_size(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    f = SolicitudFilter()
    list(svc.iter_for_admin(filters=f, chunk_size=250))
    assert repo.calls == [
        ("iter_for_admin", {"filters": f, "chunk_size": 250})
    ]


def test_iter_for_admin_default_chunk_size_is_500(svc_and_repo) -> None:
    svc, repo = svc_and_repo
    list(svc.iter_for_admin(filters=SolicitudFilter()))
    assert repo.calls[0][1]["chunk_size"] == 500
