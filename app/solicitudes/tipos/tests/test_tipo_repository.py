"""Tests for the ORM-backed TipoRepository."""
from __future__ import annotations

from uuid import uuid4

import pytest

from solicitudes.models import FieldDefinition, TipoSolicitud
from solicitudes.tipos.constants import FieldSource, FieldType
from solicitudes.tipos.exceptions import TipoNotFound
from solicitudes.tipos.repositories.tipo import OrmTipoRepository
from solicitudes.tipos.schemas import (
    CreateFieldInput,
    CreateTipoInput,
    TipoSolicitudDTO,
    UpdateTipoInput,
)
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import Role


@pytest.fixture
def repo() -> OrmTipoRepository:
    return OrmTipoRepository()


# ---------- create ----------


@pytest.mark.django_db
def test_create_persists_tipo_and_fields(repo: OrmTipoRepository) -> None:
    dto = repo.create(
        CreateTipoInput(
            nombre="Constancia de Estudios",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(label="Nombre", field_type=FieldType.TEXT, order=0),
                CreateFieldInput(
                    label="Programa",
                    field_type=FieldType.SELECT,
                    order=1,
                    options=["ISW", "ISC"],
                ),
            ],
        )
    )
    assert isinstance(dto, TipoSolicitudDTO)
    assert dto.slug == "constancia-de-estudios"
    assert dto.responsible_role is Role.CONTROL_ESCOLAR
    assert dto.creator_roles == {Role.ALUMNO}
    assert len(dto.fields) == 2
    assert [f.order for f in dto.fields] == [0, 1]
    assert TipoSolicitud.objects.count() == 1
    assert FieldDefinition.objects.count() == 2


@pytest.mark.django_db
def test_create_appends_numeric_suffix_on_slug_collision(repo: OrmTipoRepository) -> None:
    make_tipo(slug="constancia-de-estudios", nombre="Constancia de Estudios")
    dto = repo.create(
        CreateTipoInput(
            nombre="Constancia de Estudios",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
        )
    )
    assert dto.slug == "constancia-de-estudios-2"


# ---------- get ----------


@pytest.mark.django_db
def test_get_by_id_returns_dto_with_fields_ordered(repo: OrmTipoRepository) -> None:
    tipo = make_tipo()
    make_field(tipo, order=2, label="C")
    make_field(tipo, order=0, label="A")
    make_field(tipo, order=1, label="B")
    dto = repo.get_by_id(tipo.id)
    assert [f.label for f in dto.fields] == ["A", "B", "C"]


@pytest.mark.django_db
def test_get_by_id_raises_when_missing(repo: OrmTipoRepository) -> None:
    with pytest.raises(TipoNotFound):
        repo.get_by_id(uuid4())


@pytest.mark.django_db
def test_get_by_slug_raises_when_missing(repo: OrmTipoRepository) -> None:
    with pytest.raises(TipoNotFound):
        repo.get_by_slug("nope")


# ---------- list ----------


@pytest.mark.django_db
def test_list_filters_by_active_responsible_and_creator(repo: OrmTipoRepository) -> None:
    make_tipo(
        nombre="A",
        slug="a",
        activo=True,
        responsible_role=Role.CONTROL_ESCOLAR.value,
        creator_roles=[Role.ALUMNO.value],
    )
    make_tipo(
        nombre="B",
        slug="b",
        activo=False,
        responsible_role=Role.CONTROL_ESCOLAR.value,
        creator_roles=[Role.ALUMNO.value],
    )
    make_tipo(
        nombre="C",
        slug="c",
        activo=True,
        responsible_role=Role.RESPONSABLE_PROGRAMA.value,
        creator_roles=[Role.DOCENTE.value],
    )

    only_active = repo.list(only_active=True)
    assert {r.slug for r in only_active} == {"a", "c"}

    by_role = repo.list(responsible_role=Role.CONTROL_ESCOLAR)
    assert {r.slug for r in by_role} == {"a", "b"}

    by_creator = repo.list(creator_role=Role.DOCENTE)
    assert {r.slug for r in by_creator} == {"c"}


# ---------- update ----------


@pytest.mark.django_db
def test_update_replaces_fieldset_atomically_keeping_unchanged_ids(
    repo: OrmTipoRepository,
) -> None:
    tipo = make_tipo()
    f0 = make_field(tipo, order=0, label="A", field_type=FieldType.TEXT.value)
    f1 = make_field(tipo, order=1, label="B", field_type=FieldType.TEXT.value)
    # f2 will be removed in the update.
    make_field(tipo, order=2, label="C", field_type=FieldType.TEXT.value)

    dto = repo.update(
        UpdateTipoInput(
            id=tipo.id,
            nombre=tipo.nombre,
            responsible_role=Role(tipo.responsible_role),
            creator_roles={Role(r) for r in tipo.creator_roles},
            fields=[
                # Reorder + relabel an existing field; must keep its id.
                CreateFieldInput(
                    id=f1.id, label="B-renamed", field_type=FieldType.TEXT, order=0
                ),
                CreateFieldInput(
                    id=f0.id, label="A", field_type=FieldType.TEXT, order=1
                ),
                # New field with no id.
                CreateFieldInput(label="D", field_type=FieldType.NUMBER, order=2),
            ],
        )
    )
    assert FieldDefinition.objects.count() == 3
    assert {str(f.id) for f in dto.fields} >= {str(f0.id), str(f1.id)}
    assert [(f.label, f.order) for f in dto.fields] == [
        ("B-renamed", 0),
        ("A", 1),
        ("D", 2),
    ]


@pytest.mark.django_db
def test_update_raises_when_tipo_missing(repo: OrmTipoRepository) -> None:
    with pytest.raises(TipoNotFound):
        repo.update(
            UpdateTipoInput(
                id=uuid4(),
                nombre="Inexistente",
                responsible_role=Role.CONTROL_ESCOLAR,
                creator_roles={Role.ALUMNO},
            )
        )


# ---------- deactivate ----------


@pytest.mark.django_db
def test_deactivate_flips_flag(repo: OrmTipoRepository) -> None:
    tipo = make_tipo(activo=True)
    repo.deactivate(tipo.id)
    tipo.refresh_from_db()
    assert tipo.activo is False


@pytest.mark.django_db
def test_deactivate_raises_when_missing(repo: OrmTipoRepository) -> None:
    with pytest.raises(TipoNotFound):
        repo.deactivate(uuid4())


# ---------- has_solicitudes ----------


@pytest.mark.django_db
def test_has_solicitudes_returns_false_until_004(repo: OrmTipoRepository) -> None:
    tipo = make_tipo()
    # Until initiative 004 introduces the Solicitud model, this is always False.
    assert repo.has_solicitudes(tipo.id) is False


@pytest.mark.django_db
def test_max_chars_round_trips_through_repo(repo: OrmTipoRepository) -> None:
    dto = repo.create(
        CreateTipoInput(
            nombre="With max chars",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(
                    label="Nombre",
                    field_type=FieldType.TEXT,
                    order=0,
                    max_chars=120,
                ),
                CreateFieldInput(
                    label="Comentario",
                    field_type=FieldType.TEXTAREA,
                    order=1,
                    max_chars=500,
                ),
                CreateFieldInput(
                    label="Edad",
                    field_type=FieldType.NUMBER,
                    order=2,
                    max_chars=None,
                ),
            ],
        )
    )
    fetched = repo.get_by_id(dto.id)
    by_label = {f.label: f for f in fetched.fields}
    assert by_label["Nombre"].max_chars == 120
    assert by_label["Comentario"].max_chars == 500
    assert by_label["Edad"].max_chars is None


@pytest.mark.django_db
def test_source_round_trips_through_repo_on_create(repo: OrmTipoRepository) -> None:
    dto = repo.create(
        CreateTipoInput(
            nombre="With sources",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(
                    label="Programa",
                    field_type=FieldType.TEXT,
                    order=0,
                    source=FieldSource.USER_PROGRAMA,
                ),
                CreateFieldInput(
                    label="Motivo",
                    field_type=FieldType.TEXTAREA,
                    order=1,
                ),
            ],
        )
    )
    fetched = repo.get_by_id(dto.id)
    by_label = {f.label: f for f in fetched.fields}
    assert by_label["Programa"].source is FieldSource.USER_PROGRAMA
    assert by_label["Motivo"].source is FieldSource.USER_INPUT


@pytest.mark.django_db
def test_source_round_trips_through_repo_on_update(repo: OrmTipoRepository) -> None:
    dto = repo.create(
        CreateTipoInput(
            nombre="Update sources",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(
                    label="Programa",
                    field_type=FieldType.TEXT,
                    order=0,
                    source=FieldSource.USER_PROGRAMA,
                ),
            ],
        )
    )
    [existing] = dto.fields
    updated = repo.update(
        UpdateTipoInput(
            id=dto.id,
            nombre=dto.nombre,
            responsible_role=dto.responsible_role,
            creator_roles=dto.creator_roles,
            fields=[
                CreateFieldInput(
                    id=existing.id,
                    label="Programa",
                    field_type=FieldType.TEXT,
                    order=0,
                    source=FieldSource.USER_FULL_NAME,
                ),
            ],
        )
    )
    [field] = updated.fields
    assert field.id == existing.id
    assert field.source is FieldSource.USER_FULL_NAME
