"""Tests for OrmHistorialRepository."""
from __future__ import annotations

import pytest

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.repositories.historial.implementation import (
    OrmHistorialRepository,
)
from solicitudes.lifecycle.tests.factories import make_historial, make_solicitud
from usuarios.constants import Role


@pytest.fixture
def repo() -> OrmHistorialRepository:
    return OrmHistorialRepository()


@pytest.mark.django_db
def test_append_inserts_row_with_actor_role_snapshot(
    repo: OrmHistorialRepository,
) -> None:
    s = make_solicitud()
    entry = repo.append(
        folio=s.folio,
        estado_anterior=Estado.CREADA,
        estado_nuevo=Estado.EN_PROCESO,
        actor_matricula=s.solicitante_id,
        actor_role=Role.CONTROL_ESCOLAR,
        observaciones="tomada",
    )
    assert entry.estado_anterior is Estado.CREADA
    assert entry.estado_nuevo is Estado.EN_PROCESO
    assert entry.actor_role is Role.CONTROL_ESCOLAR
    assert entry.observaciones == "tomada"


@pytest.mark.django_db
def test_append_initial_creada_has_null_estado_anterior(
    repo: OrmHistorialRepository,
) -> None:
    s = make_solicitud()
    entry = repo.append(
        folio=s.folio,
        estado_anterior=None,
        estado_nuevo=Estado.CREADA,
        actor_matricula=s.solicitante_id,
        actor_role=Role.ALUMNO,
    )
    assert entry.estado_anterior is None
    assert entry.estado_nuevo is Estado.CREADA


@pytest.mark.django_db
def test_list_for_folio_returns_entries_chronologically(
    repo: OrmHistorialRepository,
) -> None:
    s = make_solicitud()
    make_historial(s, estado_nuevo=Estado.CREADA)
    make_historial(s, estado_anterior=Estado.CREADA, estado_nuevo=Estado.EN_PROCESO)
    make_historial(
        s, estado_anterior=Estado.EN_PROCESO, estado_nuevo=Estado.FINALIZADA
    )
    entries = repo.list_for_folio(s.folio)
    assert [e.estado_nuevo for e in entries] == [
        Estado.CREADA,
        Estado.EN_PROCESO,
        Estado.FINALIZADA,
    ]


@pytest.mark.django_db
def test_list_for_folio_returns_empty_when_unknown(
    repo: OrmHistorialRepository,
) -> None:
    assert repo.list_for_folio("SOL-2026-99999") == []
