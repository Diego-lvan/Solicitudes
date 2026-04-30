"""Tests for OrmSolicitudRepository aggregate methods (used by reportes)."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.repositories.historial.implementation import (
    OrmHistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.implementation import (
    OrmSolicitudRepository,
)
from solicitudes.lifecycle.schemas import SolicitudFilter
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import Solicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role


@pytest.fixture
def repo() -> OrmSolicitudRepository:
    return OrmSolicitudRepository(historial_repository=OrmHistorialRepository())


def _set_created(s: Solicitud, when: datetime) -> None:
    Solicitud.objects.filter(pk=s.folio).update(created_at=when)


@pytest.mark.django_db
def test_aggregate_by_estado_groups_and_filters(
    repo: OrmSolicitudRepository,
) -> None:
    tipo_a = make_tipo(slug="tipo-a", responsible_role=Role.CONTROL_ESCOLAR.value)
    tipo_b = make_tipo(slug="tipo-b", responsible_role=Role.RESPONSABLE_PROGRAMA.value)
    make_solicitud(tipo=tipo_a, estado=Estado.CREADA)
    make_solicitud(tipo=tipo_a, estado=Estado.CREADA)
    make_solicitud(tipo=tipo_a, estado=Estado.FINALIZADA)
    make_solicitud(tipo=tipo_b, estado=Estado.CANCELADA)

    rows = repo.aggregate_by_estado(filters=SolicitudFilter())
    counts = {r.estado: r.count for r in rows}
    assert counts == {Estado.CREADA: 2, Estado.FINALIZADA: 1, Estado.CANCELADA: 1}

    rows = repo.aggregate_by_estado(
        filters=SolicitudFilter(responsible_role=Role.CONTROL_ESCOLAR)
    )
    counts = {r.estado: r.count for r in rows}
    assert counts == {Estado.CREADA: 2, Estado.FINALIZADA: 1}


@pytest.mark.django_db
def test_aggregate_by_tipo_returns_id_name_and_count(
    repo: OrmSolicitudRepository,
) -> None:
    tipo_a = make_tipo(slug="tipo-a", nombre="Constancia")
    tipo_b = make_tipo(slug="tipo-b", nombre="Beca")
    make_solicitud(tipo=tipo_a)
    make_solicitud(tipo=tipo_a)
    make_solicitud(tipo=tipo_b)

    rows = repo.aggregate_by_tipo(filters=SolicitudFilter())
    by_id = {r.tipo_id: (r.tipo_nombre, r.count) for r in rows}
    assert by_id[tipo_a.id] == ("Constancia", 2)
    assert by_id[tipo_b.id] == ("Beca", 1)


@pytest.mark.django_db
def test_aggregate_by_month_groups_by_year_month(
    repo: OrmSolicitudRepository,
) -> None:
    tipo = make_tipo()
    s1 = make_solicitud(tipo=tipo)
    s2 = make_solicitud(tipo=tipo)
    s3 = make_solicitud(tipo=tipo)
    _set_created(s1, datetime(2026, 1, 15, 12, tzinfo=UTC))
    _set_created(s2, datetime(2026, 1, 20, 12, tzinfo=UTC))
    _set_created(s3, datetime(2026, 3, 15, 12, tzinfo=UTC))

    rows = repo.aggregate_by_month(
        filters=SolicitudFilter(
            created_from=date(2026, 1, 1), created_to=date(2026, 3, 31)
        )
    )
    by_month = {(r.year, r.month): r.count for r in rows}
    assert by_month == {(2026, 1): 2, (2026, 3): 1}


@pytest.mark.django_db
def test_aggregate_by_month_honors_date_range_filter(
    repo: OrmSolicitudRepository,
) -> None:
    tipo = make_tipo()
    in_range = make_solicitud(tipo=tipo)
    out_of_range = make_solicitud(tipo=tipo)
    _set_created(in_range, datetime(2026, 2, 10, 12, tzinfo=UTC))
    _set_created(out_of_range, datetime(2025, 12, 10, 12, tzinfo=UTC))

    rows = repo.aggregate_by_month(
        filters=SolicitudFilter(created_from=date(2026, 1, 1))
    )
    by_month = {(r.year, r.month): r.count for r in rows}
    assert by_month == {(2026, 2): 1}


@pytest.mark.django_db
def test_aggregate_methods_are_single_query_each(
    repo: OrmSolicitudRepository, django_assert_num_queries
) -> None:
    tipo = make_tipo()
    for _ in range(5):
        make_solicitud(tipo=tipo)

    with django_assert_num_queries(1):
        repo.aggregate_by_estado(filters=SolicitudFilter())
    with django_assert_num_queries(1):
        repo.aggregate_by_tipo(filters=SolicitudFilter())
    with django_assert_num_queries(1):
        repo.aggregate_by_month(filters=SolicitudFilter())
