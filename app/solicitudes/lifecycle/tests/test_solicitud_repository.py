"""Tests for OrmSolicitudRepository."""
from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from _shared.pagination import PageRequest
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.repositories.historial.implementation import (
    OrmHistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.implementation import (
    OrmSolicitudRepository,
)
from solicitudes.lifecycle.schemas import SolicitudFilter
from solicitudes.lifecycle.tests.factories import (
    make_form_snapshot,
    make_solicitud,
)
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.tests.factories import make_user


@pytest.fixture
def repo() -> OrmSolicitudRepository:
    return OrmSolicitudRepository(historial_repository=OrmHistorialRepository())


@pytest.mark.django_db
def test_create_persists_and_returns_detail(repo: OrmSolicitudRepository) -> None:
    tipo = make_tipo()
    user = make_user(matricula="ALU-1", email="alu-1@uaz.edu.mx", role=Role.ALUMNO.value)
    snapshot = make_form_snapshot(tipo)
    detail = repo.create(
        folio="SOL-2026-00001",
        tipo_id=tipo.id,
        solicitante_matricula=user.matricula,
        estado=Estado.CREADA,
        form_snapshot=snapshot,
        valores={"a": "b"},
        requiere_pago=True,
        pago_exento=False,
    )
    assert detail.folio == "SOL-2026-00001"
    assert detail.estado is Estado.CREADA
    assert detail.requiere_pago is True
    assert detail.pago_exento is False
    assert detail.valores == {"a": "b"}
    assert isinstance(detail.form_snapshot, FormSnapshot)
    assert detail.historial == []


@pytest.mark.django_db
def test_get_by_folio_raises_when_missing(repo: OrmSolicitudRepository) -> None:
    with pytest.raises(SolicitudNotFound):
        repo.get_by_folio("SOL-2026-99999")


@pytest.mark.django_db
def test_update_estado_changes_state_and_updated_at(
    repo: OrmSolicitudRepository,
) -> None:
    s = make_solicitud(estado=Estado.CREADA)
    before = s.updated_at
    repo.update_estado(s.folio, new_estado=Estado.EN_PROCESO)
    s.refresh_from_db()
    assert s.estado == Estado.EN_PROCESO.value
    assert s.updated_at > before


@pytest.mark.django_db
def test_update_estado_raises_when_missing(repo: OrmSolicitudRepository) -> None:
    with pytest.raises(SolicitudNotFound):
        repo.update_estado("SOL-2026-99999", new_estado=Estado.CANCELADA)


@pytest.mark.django_db
def test_list_for_solicitante_filters_to_owner_only(
    repo: OrmSolicitudRepository,
) -> None:
    alumno_a = make_user(matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO.value)
    alumno_b = make_user(matricula="A2", email="a2@uaz.edu.mx", role=Role.ALUMNO.value)
    make_solicitud(solicitante=alumno_a)
    make_solicitud(solicitante=alumno_a)
    make_solicitud(solicitante=alumno_b)
    page = repo.list_for_solicitante(
        "A1", page=PageRequest(), filters=SolicitudFilter()
    )
    assert page.total == 2
    assert all(r.solicitante_matricula == "A1" for r in page.items)


@pytest.mark.django_db
def test_list_for_responsible_role_uses_tipos_role(
    repo: OrmSolicitudRepository,
) -> None:
    tipo_ce = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    tipo_rp = make_tipo(responsible_role=Role.RESPONSABLE_PROGRAMA.value)
    make_solicitud(tipo=tipo_ce)
    make_solicitud(tipo=tipo_ce)
    make_solicitud(tipo=tipo_rp)
    page = repo.list_for_responsible_role(
        Role.CONTROL_ESCOLAR.value,
        page=PageRequest(),
        filters=SolicitudFilter(),
    )
    assert page.total == 2


@pytest.mark.django_db
def test_list_filters_by_estado(repo: OrmSolicitudRepository) -> None:
    user = make_user(matricula="A1")
    make_solicitud(solicitante=user, estado=Estado.CREADA)
    make_solicitud(solicitante=user, estado=Estado.FINALIZADA)
    page = repo.list_for_solicitante(
        "A1",
        page=PageRequest(),
        filters=SolicitudFilter(estado=Estado.FINALIZADA),
    )
    assert page.total == 1
    assert page.items[0].estado is Estado.FINALIZADA


@pytest.mark.django_db
def test_list_filters_by_folio_substring(repo: OrmSolicitudRepository) -> None:
    user = make_user(matricula="A1")
    make_solicitud(solicitante=user, folio="SOL-2026-00010")
    make_solicitud(solicitante=user, folio="SOL-2026-00011")
    page = repo.list_for_solicitante(
        "A1",
        page=PageRequest(),
        filters=SolicitudFilter(folio_contains="00010"),
    )
    assert {r.folio for r in page.items} == {"SOL-2026-00010"}


@pytest.mark.django_db
def test_list_pagination_returns_correct_window(
    repo: OrmSolicitudRepository,
) -> None:
    user = make_user(matricula="A1")
    for i in range(7):
        make_solicitud(solicitante=user, folio=f"SOL-2026-{i:05d}")
    page1 = repo.list_for_solicitante(
        "A1", page=PageRequest(page=1, page_size=3), filters=SolicitudFilter()
    )
    page3 = repo.list_for_solicitante(
        "A1", page=PageRequest(page=3, page_size=3), filters=SolicitudFilter()
    )
    assert page1.total == 7
    assert len(page1.items) == 3
    assert len(page3.items) == 1


@pytest.mark.django_db
def test_list_uses_at_most_three_queries(
    repo: OrmSolicitudRepository,
) -> None:
    """Acceptance criterion: list queries are at most 3 SQL queries."""
    user = make_user(matricula="A1")
    for _ in range(5):
        make_solicitud(solicitante=user)
    with CaptureQueriesContext(connection) as ctx:
        page = repo.list_for_solicitante(
            "A1", page=PageRequest(), filters=SolicitudFilter()
        )
        # Force evaluation of any iterators/computed fields.
        _ = [r.tipo_nombre for r in page.items]
    assert len(ctx) <= 3, f"too many queries: {[q['sql'] for q in ctx]}"


@pytest.mark.django_db
def test_exists_for_tipo_returns_true_when_referenced(
    repo: OrmSolicitudRepository,
) -> None:
    tipo = make_tipo()
    other = make_tipo()
    make_solicitud(tipo=tipo)
    assert repo.exists_for_tipo(tipo.id) is True
    assert repo.exists_for_tipo(other.id) is False


@pytest.mark.django_db
def test_get_by_folio_hydrates_historial(repo: OrmSolicitudRepository) -> None:
    s = make_solicitud()
    OrmHistorialRepository().append(
        folio=s.folio,
        estado_anterior=None,
        estado_nuevo=Estado.CREADA,
        actor_matricula=s.solicitante_id,
        actor_role=Role.ALUMNO,
    )
    detail = repo.get_by_folio(s.folio)
    assert len(detail.historial) == 1
    assert detail.historial[0].estado_nuevo is Estado.CREADA
