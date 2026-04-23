"""ArchivoService unit tests with in-memory fakes."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from _shared.exceptions import DomainValidationError, Unauthorized
from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.exceptions import (
    FileExtensionNotAllowed,
    FileTooLarge,
)
from solicitudes.archivos.services.archivo_service.implementation import (
    ArchivoServiceImpl,
)
from solicitudes.archivos.tests.fakes import (
    InMemoryArchivoRepository,
    InMemoryFileStorage,
    InMemoryLifecycleService,
)
from solicitudes.formularios.schemas import (
    FieldSnapshot,
    FormSnapshot,
)
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO

# -- harness --------------------------------------------------------------


def _user(matricula: str = "ALU-1", role: Role = Role.ALUMNO) -> UserDTO:
    return UserDTO(
        matricula=matricula,
        email=f"{matricula.lower()}@uaz.edu.mx",
        role=role,
    )


def _field_snap(
    *,
    field_id: UUID,
    accepted: list[str],
    max_mb: int = 10,
    field_type: FieldType = FieldType.FILE,
) -> FieldSnapshot:
    return FieldSnapshot(
        field_id=field_id,
        label="Adjunto",
        field_type=field_type,
        required=True,
        order=0,
        accepted_extensions=accepted,
        max_size_mb=max_mb,
    )


def _detail(
    *,
    folio: str = "SOL-2026-00001",
    estado: Estado = Estado.CREADA,
    solicitante: str = "ALU-1",
    responsible: Role = Role.CONTROL_ESCOLAR,
    requiere_pago: bool = False,
    pago_exento: bool = False,
    fields: list[FieldSnapshot] | None = None,
) -> SolicitudDetail:
    tipo_id = uuid4()
    snap = FormSnapshot(
        tipo_id=tipo_id,
        tipo_slug="constancia",
        tipo_nombre="Constancia",
        captured_at=datetime.now(tz=UTC),
        fields=fields or [],
    )
    return SolicitudDetail(
        folio=folio,
        tipo=TipoSolicitudRow(
            id=tipo_id,
            slug="constancia",
            nombre="Constancia",
            responsible_role=responsible,
            creator_roles={Role.ALUMNO},
            requires_payment=requiere_pago,
            activo=True,
        ),
        solicitante=UserDTO(
            matricula=solicitante,
            email=f"{solicitante.lower()}@uaz.edu.mx",
            role=Role.ALUMNO,
        ),
        estado=estado,
        form_snapshot=snap,
        valores={},
        requiere_pago=requiere_pago,
        pago_exento=pago_exento,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        historial=[],
    )


def _service(
    details: list[SolicitudDetail] | None = None,
) -> tuple[
    ArchivoServiceImpl,
    InMemoryArchivoRepository,
    InMemoryFileStorage,
    InMemoryLifecycleService,
]:
    repo = InMemoryArchivoRepository()
    storage = InMemoryFileStorage()
    lifecycle = InMemoryLifecycleService()
    for d in details or []:
        lifecycle.register(d)
    svc = ArchivoServiceImpl(
        repository=repo, storage=storage, lifecycle=lifecycle
    )
    return svc, repo, storage, lifecycle


def _upload(
    name: str = "doc.pdf",
    *,
    content: bytes = b"hello",
    content_type: str = "application/pdf",
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


# -- store_for_solicitud --------------------------------------------------


def test_store_form_field_happy_path() -> None:
    field_id = uuid4()
    detail = _detail(fields=[_field_snap(field_id=field_id, accepted=[".pdf", ".zip"])])
    svc, repo, storage, _ = _service([detail])
    dto = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload("Final.PDF", content=b"abc"),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    assert dto.kind is ArchivoKind.FORM
    assert dto.field_id == field_id
    assert dto.size_bytes == 3
    [rel] = list(storage.files.keys())
    assert storage.files[rel] == b"abc"
    rec = repo.get_record(dto.id)
    assert rec.sha256 != ""


def test_store_form_field_unknown_field_raises() -> None:
    detail = _detail(fields=[])
    svc, *_ = _service([detail])
    with pytest.raises(DomainValidationError):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=uuid4(),
            kind=ArchivoKind.FORM,
            uploaded_file=_upload(),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


def test_store_form_field_disallowed_extension() -> None:
    field_id = uuid4()
    detail = _detail(fields=[_field_snap(field_id=field_id, accepted=[".pdf"])])
    svc, *_ = _service([detail])
    with pytest.raises(FileExtensionNotAllowed):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=field_id,
            kind=ArchivoKind.FORM,
            uploaded_file=_upload("evil.exe", content_type="application/x-msdownload"),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


def test_store_form_field_too_large_per_field_cap() -> None:
    field_id = uuid4()
    detail = _detail(
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"], max_mb=1)]
    )
    svc, *_ = _service([detail])
    big = _upload(content=b"x" * (2 * 1024 * 1024))
    with pytest.raises(FileTooLarge) as exc:
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=field_id,
            kind=ArchivoKind.FORM,
            uploaded_file=big,
            uploader=_user(matricula=detail.solicitante.matricula),
        )
    assert exc.value.max_bytes == 1 * 1024 * 1024


def test_store_form_field_global_cap_caps_field_cap() -> None:
    field_id = uuid4()
    detail = _detail(
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"], max_mb=999)]
    )
    svc, *_ = _service([detail])
    big = _upload(content=b"x" * (11 * 1024 * 1024))
    with pytest.raises(FileTooLarge) as exc:
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=field_id,
            kind=ArchivoKind.FORM,
            uploaded_file=big,
            uploader=_user(matricula=detail.solicitante.matricula),
        )
    assert exc.value.max_bytes == 10 * 1024 * 1024


def test_store_form_blocked_when_estado_not_creada() -> None:
    field_id = uuid4()
    detail = _detail(
        estado=Estado.EN_PROCESO,
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"])],
    )
    svc, *_ = _service([detail])
    with pytest.raises(DomainValidationError):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=field_id,
            kind=ArchivoKind.FORM,
            uploaded_file=_upload(),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


@pytest.mark.django_db
def test_store_replaces_prior_form_archivo() -> None:
    field_id = uuid4()
    detail = _detail(fields=[_field_snap(field_id=field_id, accepted=[".pdf"])])
    svc, _repo, _storage, _ = _service([detail])
    first = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(content=b"v1"),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    second = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(content=b"v2"),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    assert first.id != second.id
    surviving = svc.list_for_solicitud(detail.folio)
    assert {a.id for a in surviving} == {second.id}
    # Storage delete is scheduled via on_commit, so without a real DB
    # transaction the in-memory storage's `deleted` list stays empty here.
    # The real-DB integration test (`test_e2e_tier1`) covers the commit path.


def test_store_comprobante_requires_payment_flag() -> None:
    detail = _detail(requiere_pago=False)
    svc, *_ = _service([detail])
    with pytest.raises(DomainValidationError):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=None,
            kind=ArchivoKind.COMPROBANTE,
            uploaded_file=_upload(),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


def test_store_comprobante_blocked_when_exento() -> None:
    detail = _detail(requiere_pago=True, pago_exento=True)
    svc, *_ = _service([detail])
    with pytest.raises(DomainValidationError):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=None,
            kind=ArchivoKind.COMPROBANTE,
            uploaded_file=_upload(),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


def test_store_comprobante_extension_whitelist() -> None:
    detail = _detail(requiere_pago=True)
    svc, *_ = _service([detail])
    with pytest.raises(FileExtensionNotAllowed):
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=None,
            kind=ArchivoKind.COMPROBANTE,
            uploaded_file=_upload("bad.exe"),
            uploader=_user(matricula=detail.solicitante.matricula),
        )


@pytest.mark.django_db
def test_store_comprobante_happy_path_replace() -> None:
    detail = _detail(requiere_pago=True)
    svc, *_ = _service([detail])
    a = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=None,
        kind=ArchivoKind.COMPROBANTE,
        uploaded_file=_upload("r1.pdf"),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    b = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=None,
        kind=ArchivoKind.COMPROBANTE,
        uploaded_file=_upload("r2.png", content_type="image/png"),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    assert a.id != b.id


def test_store_comprobante_global_10mb_cap() -> None:
    detail = _detail(requiere_pago=True)
    svc, *_ = _service([detail])
    big = _upload("r.pdf", content=b"x" * (11 * 1024 * 1024))
    with pytest.raises(FileTooLarge) as exc:
        svc.store_for_solicitud(
            folio=detail.folio,
            field_id=None,
            kind=ArchivoKind.COMPROBANTE,
            uploaded_file=big,
            uploader=_user(matricula=detail.solicitante.matricula),
        )
    assert exc.value.max_bytes == 10 * 1024 * 1024


def test_store_unknown_solicitud_raises() -> None:
    svc, *_ = _service([])
    with pytest.raises(SolicitudNotFound):
        svc.store_for_solicitud(
            folio="SOL-NOPE",
            field_id=uuid4(),
            kind=ArchivoKind.FORM,
            uploaded_file=_upload(),
            uploader=_user(),
        )


# -- open_for_download authorisation -------------------------------------


def test_open_allows_solicitante() -> None:
    field_id = uuid4()
    detail = _detail(
        solicitante="ALU-1",
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"])],
    )
    svc, *_ = _service([detail])
    dto = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(),
        uploader=_user(matricula="ALU-1"),
    )
    out_dto, stream = svc.open_for_download(dto.id, _user("ALU-1"))
    assert out_dto.id == dto.id
    assert stream.read() == b"hello"


def test_open_allows_responsible_role() -> None:
    field_id = uuid4()
    detail = _detail(
        responsible=Role.CONTROL_ESCOLAR,
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"])],
    )
    svc, *_ = _service([detail])
    dto = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    out_dto, _stream = svc.open_for_download(
        dto.id, _user("PER-1", Role.CONTROL_ESCOLAR)
    )
    assert out_dto.id == dto.id


def test_open_allows_admin() -> None:
    field_id = uuid4()
    detail = _detail(fields=[_field_snap(field_id=field_id, accepted=[".pdf"])])
    svc, *_ = _service([detail])
    dto = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    out_dto, _stream = svc.open_for_download(dto.id, _user("ADM-1", Role.ADMIN))
    assert out_dto.id == dto.id


def test_open_blocks_unrelated_user() -> None:
    field_id = uuid4()
    detail = _detail(
        responsible=Role.CONTROL_ESCOLAR,
        fields=[_field_snap(field_id=field_id, accepted=[".pdf"])],
    )
    svc, *_ = _service([detail])
    dto = svc.store_for_solicitud(
        folio=detail.folio,
        field_id=field_id,
        kind=ArchivoKind.FORM,
        uploaded_file=_upload(),
        uploader=_user(matricula=detail.solicitante.matricula),
    )
    with pytest.raises(Unauthorized):
        svc.open_for_download(dto.id, _user("OTHER", Role.DOCENTE))
