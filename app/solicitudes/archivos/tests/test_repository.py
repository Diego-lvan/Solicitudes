"""Tests for OrmArchivoRepository."""
from __future__ import annotations

from uuid import uuid4

import pytest

from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.exceptions import ArchivoNotFound
from solicitudes.archivos.repositories.archivo.implementation import (
    OrmArchivoRepository,
)
from solicitudes.archivos.tests.factories import make_archivo
from solicitudes.lifecycle.tests.factories import make_solicitud


@pytest.fixture
def repo() -> OrmArchivoRepository:
    return OrmArchivoRepository()


@pytest.mark.django_db
def test_create_returns_dto(repo: OrmArchivoRepository) -> None:
    solicitud = make_solicitud()
    field_id = uuid4()
    dto = repo.create(
        solicitud_folio=solicitud.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        original_filename="x.pdf",
        stored_path=f"solicitudes/{solicitud.folio}/abc.pdf",
        content_type="application/pdf",
        size_bytes=2048,
        sha256="0" * 64,
        uploaded_by_matricula=solicitud.solicitante_id,
    )
    assert dto.kind is ArchivoKind.FORM
    assert dto.solicitud_folio == solicitud.folio
    assert dto.field_id == field_id
    assert dto.size_bytes == 2048


@pytest.mark.django_db
def test_get_record_returns_storage_fields(repo: OrmArchivoRepository) -> None:
    solicitud = make_solicitud()
    archivo = make_archivo(solicitud=solicitud)
    record = repo.get_record(archivo.id)
    assert record.solicitud_folio == solicitud.folio
    assert record.stored_path == archivo.stored_path
    assert record.kind is ArchivoKind(archivo.kind)
    assert record.size_bytes == archivo.size_bytes


@pytest.mark.django_db
def test_get_record_missing_raises(repo: OrmArchivoRepository) -> None:
    with pytest.raises(ArchivoNotFound):
        repo.get_record(uuid4())


@pytest.mark.django_db
def test_list_by_folio_oldest_first(repo: OrmArchivoRepository) -> None:
    solicitud = make_solicitud()
    a1 = make_archivo(solicitud=solicitud)
    a2 = make_archivo(solicitud=solicitud)
    rows = repo.list_by_folio(solicitud.folio)
    assert [r.id for r in rows] == [a1.id, a2.id]


@pytest.mark.django_db
def test_find_form_archivo_returns_match(repo: OrmArchivoRepository) -> None:
    solicitud = make_solicitud()
    field_id = uuid4()
    archivo = make_archivo(solicitud=solicitud, field_id=field_id)
    record = repo.find_form_archivo(folio=solicitud.folio, field_id=field_id)
    assert record is not None
    assert record.id == archivo.id


@pytest.mark.django_db
def test_find_form_archivo_returns_none_when_absent(
    repo: OrmArchivoRepository,
) -> None:
    solicitud = make_solicitud()
    assert (
        repo.find_form_archivo(folio=solicitud.folio, field_id=uuid4()) is None
    )


@pytest.mark.django_db
def test_find_comprobante(repo: OrmArchivoRepository) -> None:
    solicitud = make_solicitud()
    archivo = make_archivo(solicitud=solicitud, kind=ArchivoKind.COMPROBANTE)
    record = repo.find_comprobante(folio=solicitud.folio)
    assert record is not None
    assert record.id == archivo.id


@pytest.mark.django_db
def test_partial_unique_constraint_blocks_duplicate_form(
    repo: OrmArchivoRepository,
) -> None:
    """The partial unique index forbids two FORM rows on the same (folio, field_id)."""
    from django.db import IntegrityError

    solicitud = make_solicitud()
    field_id = uuid4()
    make_archivo(solicitud=solicitud, field_id=field_id)
    with pytest.raises(IntegrityError):
        make_archivo(solicitud=solicitud, field_id=field_id)


@pytest.mark.django_db
def test_partial_unique_constraint_blocks_duplicate_comprobante(
    repo: OrmArchivoRepository,
) -> None:
    from django.db import IntegrityError

    solicitud = make_solicitud()
    make_archivo(solicitud=solicitud, kind=ArchivoKind.COMPROBANTE)
    with pytest.raises(IntegrityError):
        make_archivo(solicitud=solicitud, kind=ArchivoKind.COMPROBANTE)


@pytest.mark.django_db
def test_delete_returns_stored_path_and_removes_row(
    repo: OrmArchivoRepository,
) -> None:
    archivo = make_archivo()
    path = repo.delete(archivo.id)
    assert path == archivo.stored_path
    with pytest.raises(ArchivoNotFound):
        repo.get_record(archivo.id)


@pytest.mark.django_db
def test_delete_missing_raises(repo: OrmArchivoRepository) -> None:
    with pytest.raises(ArchivoNotFound):
        repo.delete(uuid4())
