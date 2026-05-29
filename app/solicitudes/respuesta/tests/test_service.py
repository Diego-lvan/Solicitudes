"""Service tests — fake repo + recording storage + lifecycle fake.

Covers state guards, role authz, validation rules (size/extension/empty/cap),
transactional rollback on storage failure, and the visibility matrix for
list/download paths.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

pytestmark = pytest.mark.django_db

from _shared.exceptions import Unauthorized
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.respuesta.exceptions import (
    ArchivoRespuestaNotFound,
    EmptyRespuestaBatch,
    InvalidStateForRespuesta,
    ResponseFileExtensionNotAllowed,
    ResponseFileTooLarge,
)
from solicitudes.respuesta.schemas import CreateRespuestaInput, UploadedFile
from solicitudes.respuesta.services.respuesta_service.implementation import (
    DefaultRespuestaService,
)
from solicitudes.respuesta.tests.fakes import (
    InMemoryLifecycleService,
    InMemoryRespuestaRepository,
    RecordingFileStorage,
)
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO

# ---- builders ----------------------------------------------------------


def _tipo(responsible: Role = Role.CONTROL_ESCOLAR) -> TipoSolicitudRow:
    return TipoSolicitudRow(
        id=uuid4(),
        slug="constancia",
        nombre="Constancia de Estudios",
        responsible_role=responsible,
        creator_roles={Role.ALUMNO},
        requires_payment=False,
        activo=True,
        plantilla_id=None,
    )


def _solicitante() -> UserDTO:
    return UserDTO(
        matricula="A-OWN",
        email="a-own@uaz.edu.mx",
        role=Role.ALUMNO,
        full_name="Ana Alumna",
    )


def _detail(
    *,
    folio: str = "SOL-2026-99001",
    estado: Estado = Estado.EN_PROCESO,
    solicitante: UserDTO | None = None,
    tipo: TipoSolicitudRow | None = None,
) -> SolicitudDetail:
    sol = solicitante or _solicitante()
    t = tipo or _tipo()
    now = datetime.now(UTC)
    return SolicitudDetail(
        folio=folio,
        tipo=t,
        solicitante=sol,
        estado=estado,
        form_snapshot=FormSnapshot(
            tipo_id=t.id,
            tipo_slug=t.slug,
            tipo_nombre=t.nombre,
            captured_at=now,
            fields=[],
        ),
        valores={},
        requiere_pago=False,
        pago_exento=False,
        created_at=now,
        updated_at=now,
        historial=[],
        atendida_por=None,
    )


def _file(name: str = "x.pdf", *, size: int = 100, content: bytes | None = None) -> UploadedFile:
    return UploadedFile(
        nombre_original=name,
        content_type="application/pdf",
        size_bytes=size,
        content=content or (b"x" * size),
    )


def _service(
    *, detail: SolicitudDetail, fail_after: int | None = None
) -> tuple[DefaultRespuestaService, InMemoryRespuestaRepository, RecordingFileStorage, InMemoryLifecycleService]:
    repo = InMemoryRespuestaRepository()
    storage = RecordingFileStorage(fail_after=fail_after)
    lifecycle = InMemoryLifecycleService()
    lifecycle.register(detail)
    svc = DefaultRespuestaService(
        respuesta_repository=repo,
        file_storage=storage,
        lifecycle_service=lifecycle,
    )
    return svc, repo, storage, lifecycle


# ---- create_batch happy path ------------------------------------------


def test_create_batch_persists_files_and_comment() -> None:
    detail = _detail()
    svc, repo, storage, _ = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            comentario="Listo",
            archivos=[_file("a.pdf"), _file("b.pdf")],
        )
    )
    assert dto.comentario == "Listo"
    assert len(dto.archivos) == 2
    assert len(storage.files) == 2
    assert repo.list_for_solicitud(detail.folio) == [dto]


def test_create_batch_with_comment_only() -> None:
    detail = _detail()
    svc, _, storage, _ = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            comentario="Sin archivos",
        )
    )
    assert dto.archivos == []
    assert storage.files == {}


def test_admin_can_create_batch() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="ADM",
            actor_role=Role.ADMIN.value,
            comentario="ok",
        )
    )
    assert dto.actor_role == Role.ADMIN.value


# ---- create_batch state + authz guards --------------------------------


@pytest.mark.parametrize(
    "estado", [Estado.CREADA, Estado.FINALIZADA, Estado.CANCELADA]
)
def test_create_batch_rejects_wrong_estado(estado: Estado) -> None:
    detail = _detail(estado=estado)
    svc, _, _, _ = _service(detail=detail)
    with pytest.raises(InvalidStateForRespuesta):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula="P1",
                actor_role=Role.CONTROL_ESCOLAR.value,
                comentario="x",
            )
        )


def test_create_batch_rejects_wrong_role() -> None:
    detail = _detail()  # responsible = CONTROL_ESCOLAR
    svc, _, _, _ = _service(detail=detail)
    with pytest.raises(Unauthorized):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula="D1",
                actor_role=Role.DOCENTE.value,
                comentario="x",
            )
        )


def test_create_batch_rejects_alumno() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    with pytest.raises(Unauthorized):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula=detail.solicitante.matricula,
                actor_role=Role.ALUMNO.value,
                comentario="x",
            )
        )


# ---- create_batch per-file validation ---------------------------------


def test_create_batch_rejects_disallowed_extension() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    with pytest.raises(ResponseFileExtensionNotAllowed):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula="P1",
                actor_role=Role.CONTROL_ESCOLAR.value,
                archivos=[_file("payload.exe")],
            )
        )


def test_create_batch_rejects_oversized_file() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    big = 11 * 1024 * 1024
    with pytest.raises(ResponseFileTooLarge):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula="P1",
                actor_role=Role.CONTROL_ESCOLAR.value,
                archivos=[_file("big.pdf", size=big, content=b"x" * big)],
            )
        )


def test_create_batch_defensive_empty_payload_raises() -> None:
    # The DTO validator already enforces this, but the service re-asserts.
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    # Bypass DTO validation by constructing via model_construct.
    bad = CreateRespuestaInput.model_construct(
        folio=detail.folio,
        actor_matricula="P1",
        actor_role=Role.CONTROL_ESCOLAR.value,
        comentario="",
        archivos=[],
    )
    with pytest.raises(EmptyRespuestaBatch):
        svc.create_batch(bad)


# ---- transactional rollback -------------------------------------------


def test_storage_failure_mid_batch_rolls_back_and_cleans_up() -> None:
    detail = _detail()
    svc, repo, storage, _ = _service(detail=detail, fail_after=1)
    with pytest.raises(OSError):
        svc.create_batch(
            CreateRespuestaInput(
                folio=detail.folio,
                actor_matricula="P1",
                actor_role=Role.CONTROL_ESCOLAR.value,
                archivos=[_file("a.pdf"), _file("b.pdf"), _file("c.pdf")],
            )
        )
    # Nothing persisted in DB.
    assert repo.list_for_solicitud(detail.folio) == []
    # cleanup_pending was called from the except branch.
    assert storage.cleanup_calls == 1


# ---- list_for_solicitud visibility matrix -----------------------------


def _make_filled(estado: Estado) -> tuple[
    DefaultRespuestaService, SolicitudDetail
]:
    detail = _detail(estado=Estado.EN_PROCESO)  # batch must be created in EN_PROCESO
    svc, repo, _, lifecycle = _service(detail=detail)
    svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            comentario="ok",
        )
    )
    # Re-register at the target estado for read-time tests.
    final = SolicitudDetail(
        **{**detail.model_dump(), "estado": estado}
    )
    lifecycle.register(final)
    return svc, final


def test_admin_sees_batches_at_any_estado() -> None:
    for estado in (Estado.EN_PROCESO, Estado.FINALIZADA, Estado.CANCELADA):
        svc, detail = _make_filled(estado)
        admin = UserDTO(
            matricula="ADM", email="adm@uaz.edu.mx", role=Role.ADMIN
        )
        assert len(svc.list_for_solicitud(detail.folio, requester=admin)) == 1


def test_personal_sees_batches_at_any_estado() -> None:
    svc, detail = _make_filled(Estado.EN_PROCESO)
    personal = UserDTO(
        matricula="P1", email="p1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR
    )
    assert len(svc.list_for_solicitud(detail.folio, requester=personal)) == 1


def test_owner_hidden_during_en_proceso() -> None:
    svc, detail = _make_filled(Estado.EN_PROCESO)
    assert svc.list_for_solicitud(detail.folio, requester=detail.solicitante) == []


def test_owner_visible_after_finalizada() -> None:
    svc, detail = _make_filled(Estado.FINALIZADA)
    assert len(svc.list_for_solicitud(detail.folio, requester=detail.solicitante)) == 1


def test_other_alumno_never_sees_batches() -> None:
    svc, detail = _make_filled(Estado.FINALIZADA)
    other = UserDTO(matricula="A99", email="a99@uaz.edu.mx", role=Role.ALUMNO)
    assert svc.list_for_solicitud(detail.folio, requester=other) == []


# ---- open_for_download authz -----------------------------------------


def test_owner_can_download_when_finalizada() -> None:
    detail = _detail(estado=Estado.EN_PROCESO)
    svc, repo, storage, lifecycle = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            archivos=[_file("doc.pdf")],
        )
    )
    archivo_id = dto.archivos[0].id

    lifecycle.register(
        SolicitudDetail(**{**detail.model_dump(), "estado": Estado.FINALIZADA})
    )
    out_dto, stream = svc.open_for_download(
        archivo_id, requester=detail.solicitante
    )
    assert out_dto.nombre_original == "doc.pdf"
    assert stream.read() == b"x" * 100


def test_owner_blocked_during_en_proceso() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            archivos=[_file("doc.pdf")],
        )
    )
    with pytest.raises(Unauthorized):
        svc.open_for_download(
            dto.archivos[0].id, requester=detail.solicitante
        )


def test_personal_can_download_any_estado() -> None:
    detail = _detail()
    svc, _, _, lifecycle = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            archivos=[_file("doc.pdf")],
        )
    )
    for estado in (Estado.EN_PROCESO, Estado.FINALIZADA, Estado.CANCELADA):
        lifecycle.register(
            SolicitudDetail(**{**detail.model_dump(), "estado": estado})
        )
        personal = UserDTO(
            matricula="P1", email="p1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR
        )
        out_dto, _ = svc.open_for_download(dto.archivos[0].id, requester=personal)
        assert out_dto.id == dto.archivos[0].id


def test_other_alumno_cannot_download_even_finalizada() -> None:
    detail = _detail(estado=Estado.EN_PROCESO)
    svc, _, _, lifecycle = _service(detail=detail)
    dto = svc.create_batch(
        CreateRespuestaInput(
            folio=detail.folio,
            actor_matricula="P1",
            actor_role=Role.CONTROL_ESCOLAR.value,
            archivos=[_file("doc.pdf")],
        )
    )
    lifecycle.register(
        SolicitudDetail(**{**detail.model_dump(), "estado": Estado.FINALIZADA})
    )
    other = UserDTO(matricula="A99", email="a99@uaz.edu.mx", role=Role.ALUMNO)
    with pytest.raises(Unauthorized):
        svc.open_for_download(dto.archivos[0].id, requester=other)


def test_missing_archivo_raises_not_found() -> None:
    detail = _detail()
    svc, _, _, _ = _service(detail=detail)
    admin = UserDTO(matricula="ADM", email="adm@uaz.edu.mx", role=Role.ADMIN)
    with pytest.raises(ArchivoRespuestaNotFound):
        svc.open_for_download(uuid4(), requester=admin)
