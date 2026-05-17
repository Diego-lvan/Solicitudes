"""Repository tests — real DB, DTO assertions, append-only contract."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.respuesta.exceptions import ArchivoRespuestaNotFound
from solicitudes.respuesta.repositories.respuesta.implementation import (
    OrmRespuestaRepository,
)
from solicitudes.respuesta.schemas import ArchivoRespuestaRecord
from usuarios.constants import Role
from usuarios.tests.factories import make_user


def _record(folio: str, name: str = "x.pdf") -> ArchivoRespuestaRecord:
    return ArchivoRespuestaRecord(
        id=uuid4(),
        respuesta_id=uuid4(),  # overwritten on insert
        folio=folio,
        nombre_original=name,
        stored_path=f"solicitudes/{folio}/{uuid4().hex}.pdf",
        content_type="application/pdf",
        size_bytes=128,
        sha256=sha256(name.encode()).hexdigest(),
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.django_db
def test_create_persists_batch_with_files() -> None:
    sol = make_solicitud()
    actor = make_user(
        matricula="P-REPO", email="p-repo@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    repo = OrmRespuestaRepository()

    dto = repo.create(
        folio=sol.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="Constancia firmada",
        archivos=[_record(sol.folio, "constancia.pdf"), _record(sol.folio, "anexo.pdf")],
    )

    assert dto.folio == sol.folio
    assert dto.actor_matricula == actor.matricula
    assert dto.comentario == "Constancia firmada"
    assert len(dto.archivos) == 2
    assert {a.nombre_original for a in dto.archivos} == {"constancia.pdf", "anexo.pdf"}


@pytest.mark.django_db
def test_comment_only_batch_persists_with_zero_files() -> None:
    sol = make_solicitud()
    actor = make_user(
        matricula="P-COM", email="p-com@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    dto = OrmRespuestaRepository().create(
        folio=sol.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="Solo comentario",
        archivos=[],
    )
    assert dto.archivos == []
    assert dto.comentario == "Solo comentario"


@pytest.mark.django_db
def test_list_returns_batches_oldest_first() -> None:
    sol = make_solicitud()
    actor = make_user(
        matricula="P-LST", email="p-lst@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    repo = OrmRespuestaRepository()

    repo.create(
        folio=sol.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="Primero",
        archivos=[],
    )
    repo.create(
        folio=sol.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="Segundo",
        archivos=[_record(sol.folio)],
    )

    rows = repo.list_for_solicitud(sol.folio)
    assert [b.comentario for b in rows] == ["Primero", "Segundo"]


@pytest.mark.django_db
def test_list_isolates_by_folio() -> None:
    sol_a = make_solicitud()
    sol_b = make_solicitud()
    actor = make_user(
        matricula="P-ISO", email="p-iso@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    repo = OrmRespuestaRepository()
    repo.create(
        folio=sol_a.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="A",
        archivos=[],
    )
    repo.create(
        folio=sol_b.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="B",
        archivos=[],
    )
    assert [b.comentario for b in repo.list_for_solicitud(sol_a.folio)] == ["A"]
    assert [b.comentario for b in repo.list_for_solicitud(sol_b.folio)] == ["B"]


@pytest.mark.django_db
def test_get_archivo_record_returns_record_with_stored_path() -> None:
    sol = make_solicitud()
    actor = make_user(
        matricula="P-ARC", email="p-arc@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    repo = OrmRespuestaRepository()
    dto = repo.create(
        folio=sol.folio,
        actor_matricula=actor.matricula,
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="",
        archivos=[_record(sol.folio, "alpha.pdf")],
    )

    archivo = dto.archivos[0]
    record = repo.get_archivo_record(archivo.id)

    assert record.id == archivo.id
    assert record.folio == sol.folio
    assert record.nombre_original == "alpha.pdf"
    assert record.stored_path.startswith(f"solicitudes/{sol.folio}/")


@pytest.mark.django_db
def test_get_archivo_record_missing_raises_not_found() -> None:
    with pytest.raises(ArchivoRespuestaNotFound):
        OrmRespuestaRepository().get_archivo_record(uuid4())


def test_repository_interface_has_no_delete_method() -> None:
    """Append-only at the app layer: there is no in-app delete path."""
    repo = OrmRespuestaRepository()
    assert not hasattr(repo, "delete")
    assert not hasattr(repo, "delete_batch")
    assert not hasattr(repo, "delete_archivo")
