"""Tests for the ORM-backed PlantillaRepository."""
from __future__ import annotations

from uuid import uuid4

import pytest

from solicitudes.models import PlantillaSolicitud
from solicitudes.pdf.exceptions import PlantillaNotFound
from solicitudes.pdf.repositories.plantilla import OrmPlantillaRepository
from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    UpdatePlantillaInput,
)
from solicitudes.pdf.tests.factories import make_plantilla


@pytest.fixture
def repo() -> OrmPlantillaRepository:
    return OrmPlantillaRepository()


@pytest.mark.django_db
def test_create_persists_and_returns_dto(repo: OrmPlantillaRepository) -> None:
    dto = repo.create(
        CreatePlantillaInput(
            nombre="Constancia",
            descripcion="d",
            html="<p>{{ solicitante.nombre }}</p>",
            css="@page { size: A4; }",
        )
    )
    assert isinstance(dto, PlantillaDTO)
    assert PlantillaSolicitud.objects.count() == 1
    assert dto.nombre == "Constancia"
    assert dto.activo is True


@pytest.mark.django_db
def test_get_by_id_returns_dto(repo: OrmPlantillaRepository) -> None:
    p = make_plantilla(nombre="X")
    dto = repo.get_by_id(p.id)
    assert dto.id == p.id
    assert dto.nombre == "X"


@pytest.mark.django_db
def test_get_by_id_missing_raises(repo: OrmPlantillaRepository) -> None:
    with pytest.raises(PlantillaNotFound):
        repo.get_by_id(uuid4())


@pytest.mark.django_db
def test_list_orders_and_filters(repo: OrmPlantillaRepository) -> None:
    make_plantilla(nombre="B", activo=True)
    make_plantilla(nombre="A", activo=True)
    make_plantilla(nombre="C", activo=False)

    all_rows = repo.list()
    assert [r.nombre for r in all_rows] == ["A", "B", "C"]

    only_active = repo.list(only_active=True)
    assert [r.nombre for r in only_active] == ["A", "B"]


@pytest.mark.django_db
def test_update_replaces_fields(repo: OrmPlantillaRepository) -> None:
    p = make_plantilla(nombre="Old")
    dto = repo.update(
        UpdatePlantillaInput(
            id=p.id,
            nombre="New",
            descripcion="dd",
            html="<p>x</p>",
            css="",
            activo=False,
        )
    )
    assert dto.nombre == "New"
    assert dto.activo is False
    p.refresh_from_db()
    assert p.nombre == "New"


@pytest.mark.django_db
def test_update_missing_raises(repo: OrmPlantillaRepository) -> None:
    with pytest.raises(PlantillaNotFound):
        repo.update(
            UpdatePlantillaInput(
                id=uuid4(), nombre="x" * 5, html="<p/>", descripcion="", css=""
            )
        )


@pytest.mark.django_db
def test_deactivate_sets_inactive(repo: OrmPlantillaRepository) -> None:
    p = make_plantilla(activo=True)
    repo.deactivate(p.id)
    p.refresh_from_db()
    assert p.activo is False


@pytest.mark.django_db
def test_deactivate_missing_raises(repo: OrmPlantillaRepository) -> None:
    with pytest.raises(PlantillaNotFound):
        repo.deactivate(uuid4())
