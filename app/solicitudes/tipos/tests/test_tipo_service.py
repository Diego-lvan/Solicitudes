"""Tests for the DefaultTipoService (in-memory fake repository)."""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from freezegun import freeze_time

from _shared.exceptions import Unauthorized
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.exceptions import TipoNotFound
from solicitudes.tipos.schemas import (
    CreateFieldInput,
    CreateTipoInput,
    TipoSolicitudDTO,
    UpdateTipoInput,
)
from solicitudes.tipos.services.tipo_service import DefaultTipoService
from solicitudes.tipos.tests.fakes import InMemoryTipoRepository
from usuarios.constants import Role


@pytest.fixture
def repo() -> InMemoryTipoRepository:
    return InMemoryTipoRepository()


@pytest.fixture
def service(repo: InMemoryTipoRepository) -> DefaultTipoService:
    return DefaultTipoService(tipo_repository=repo)


def _seed_tipo(
    repo: InMemoryTipoRepository,
    *,
    slug: str = "constancia-de-estudios",
    nombre: str = "Constancia de Estudios",
    activo: bool = True,
    creator_roles: frozenset[Role] | set[Role] = frozenset({Role.ALUMNO}),
    responsible_role: Role = Role.CONTROL_ESCOLAR,
) -> TipoSolicitudDTO:
    dto = TipoSolicitudDTO(
        id=uuid4(),
        slug=slug,
        nombre=nombre,
        descripcion="",
        responsible_role=responsible_role,
        creator_roles=set(creator_roles),
        requires_payment=False,
        mentor_exempt=False,
        plantilla_id=None,
        activo=activo,
        fields=[],
    )
    return repo.seed(dto)


# ---- create ----


def test_create_passes_through_to_repository(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    dto = service.create(
        CreateTipoInput(
            nombre="Constancia de Estudios",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(label="A", field_type=FieldType.TEXT, order=0),
            ],
        )
    )
    assert dto.slug == "constancia-de-estudios"
    assert len(dto.fields) == 1
    assert repo.get_by_id(dto.id).slug == dto.slug


# ---- list_for_creator ----


def test_list_for_creator_filters_by_role_and_active(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    _seed_tipo(repo, slug="a", nombre="A", creator_roles={Role.ALUMNO})
    _seed_tipo(
        repo, slug="b", nombre="B", creator_roles={Role.ALUMNO}, activo=False
    )
    _seed_tipo(repo, slug="c", nombre="C", creator_roles={Role.DOCENTE})

    visible = service.list_for_creator(Role.ALUMNO)
    assert {r.slug for r in visible} == {"a"}


# ---- get_for_creator ----


def test_get_for_creator_rejects_role_not_in_creator_roles(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = _seed_tipo(repo, creator_roles={Role.ALUMNO})
    with pytest.raises(Unauthorized):
        service.get_for_creator(tipo.slug, Role.DOCENTE)


def test_get_for_creator_rejects_inactive_tipo(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = _seed_tipo(repo, activo=False, creator_roles={Role.ALUMNO})
    with pytest.raises(Unauthorized):
        service.get_for_creator(tipo.slug, Role.ALUMNO)


def test_get_for_creator_returns_active_tipo_for_authorized_role(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = _seed_tipo(repo, creator_roles={Role.ALUMNO})
    dto = service.get_for_creator(tipo.slug, Role.ALUMNO)
    assert dto.id == tipo.id


# ---- delete vs deactivate ----


def test_deactivate_idempotent_for_already_inactive(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = _seed_tipo(repo, activo=False)
    service.deactivate(tipo.id)
    assert repo.get_by_id(tipo.id).activo is False


def test_deactivate_raises_when_missing(service: DefaultTipoService) -> None:
    with pytest.raises(TipoNotFound):
        service.deactivate(uuid4())


# ---- snapshot ----


@freeze_time("2026-04-25T12:00:00Z")
def test_snapshot_returns_form_snapshot_at_now(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = service.create(
        CreateTipoInput(
            nombre="Constancia de Estudios",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(label="A", field_type=FieldType.TEXT, order=0),
                CreateFieldInput(
                    label="P",
                    field_type=FieldType.SELECT,
                    order=1,
                    options=["X", "Y"],
                ),
            ],
        )
    )
    snap = service.snapshot(tipo.id)
    assert isinstance(snap, FormSnapshot)
    assert snap.tipo_slug == tipo.slug
    assert snap.captured_at.year == 2026
    assert [f.label for f in snap.fields] == ["A", "P"]
    assert snap.fields[1].options == ["X", "Y"]
    # field_id matches the persisted field id so 004 can join back.
    assert isinstance(snap.fields[0].field_id, UUID)


def test_snapshot_rejects_inactive_tipo(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = _seed_tipo(repo, activo=False)
    with pytest.raises(TipoNotFound):
        service.snapshot(tipo.id)


# ---- update ----


def test_update_replaces_fieldset(
    service: DefaultTipoService, repo: InMemoryTipoRepository
) -> None:
    tipo = service.create(
        CreateTipoInput(
            nombre="Constancia de Estudios",
            responsible_role=Role.CONTROL_ESCOLAR,
            creator_roles={Role.ALUMNO},
            fields=[
                CreateFieldInput(label="A", field_type=FieldType.TEXT, order=0),
            ],
        )
    )
    original_field_id = tipo.fields[0].id
    updated = service.update(
        UpdateTipoInput(
            id=tipo.id,
            nombre=tipo.nombre,
            responsible_role=tipo.responsible_role,
            creator_roles=tipo.creator_roles,
            fields=[
                CreateFieldInput(
                    id=original_field_id,
                    label="A renamed",
                    field_type=FieldType.TEXT,
                    order=0,
                ),
                CreateFieldInput(label="B", field_type=FieldType.NUMBER, order=1),
            ],
        )
    )
    assert [f.label for f in updated.fields] == ["A renamed", "B"]
    assert updated.fields[0].id == original_field_id
