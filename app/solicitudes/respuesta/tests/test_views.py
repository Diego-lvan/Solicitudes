"""View tests for the respuesta feature.

Covers the full HTTP round-trip: upload form, download authz, and the
cross-feature Tier 1 integration flow (personal uploads → finalizes →
solicitante sees the response files).
"""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import (
    ArchivoRespuesta,
    RespuestaSolicitud,
    TipoSolicitud,
)
from solicitudes.respuesta.tests.conftest import make_client
from solicitudes.respuesta.tests.factories import (
    make_archivo_respuesta,
    make_respuesta,
)
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.tests.factories import make_user


def _tipo() -> TipoSolicitud:
    return make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)


# ---- create batch view -----------------------------------------------


@pytest.mark.django_db
def test_personal_uploads_two_files_with_comment() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    make_user(matricula="P1", email="p1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    c = make_client("P1", Role.CONTROL_ESCOLAR)

    resp = c.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={
            "comentario": "Adjunto la constancia firmada",
            "archivos": [
                SimpleUploadedFile("a.pdf", b"alpha", content_type="application/pdf"),
                SimpleUploadedFile("b.pdf", b"beta", content_type="application/pdf"),
            ],
        },
    )
    assert resp.status_code == 302
    assert resp["Location"].endswith(f"/revision/{sol.folio}/")
    assert RespuestaSolicitud.objects.filter(solicitud_id=sol.folio).count() == 1
    assert ArchivoRespuesta.objects.count() == 2
    batch = RespuestaSolicitud.objects.get(solicitud_id=sol.folio)
    assert batch.comentario == "Adjunto la constancia firmada"
    assert batch.actor.matricula == "P1"


@pytest.mark.django_db
def test_personal_can_post_comment_only() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    make_user(matricula="P2", email="p2@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    c = make_client("P2", Role.CONTROL_ESCOLAR)

    resp = c.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={"comentario": "Sin archivos por ahora"},
    )
    assert resp.status_code == 302
    assert RespuestaSolicitud.objects.filter(solicitud_id=sol.folio).count() == 1


@pytest.mark.django_db
def test_alumno_cannot_post_create() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    c = make_client(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={"comentario": "x"},
    )
    # ReviewerRequiredMixin → Unauthorized → 403 via middleware
    assert resp.status_code == 403
    assert RespuestaSolicitud.objects.count() == 0


@pytest.mark.django_db
def test_post_in_creada_estado_redirects_with_flash() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    make_user(matricula="P3", email="p3@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    c = make_client("P3", Role.CONTROL_ESCOLAR)

    resp = c.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={"comentario": "x"},
    )
    assert resp.status_code == 302
    assert RespuestaSolicitud.objects.count() == 0


@pytest.mark.django_db
def test_empty_submission_redirects_without_creating() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    make_user(matricula="P4", email="p4@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    c = make_client("P4", Role.CONTROL_ESCOLAR)

    resp = c.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={"comentario": ""},
    )
    assert resp.status_code == 302
    assert RespuestaSolicitud.objects.count() == 0


# ---- download view ---------------------------------------------------


@pytest.mark.django_db
def test_owner_cannot_download_during_en_proceso() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    actor = make_user(
        matricula="P5", email="p5@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    batch = make_respuesta(
        solicitud=sol, actor=actor, actor_role=Role.CONTROL_ESCOLAR
    )
    archivo = make_archivo_respuesta(respuesta=batch)

    c = make_client(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.get(
        reverse(
            "solicitudes:respuesta:download",
            kwargs={
                "folio": sol.folio,
                "respuesta_id": batch.id,
                "archivo_id": archivo.id,
            },
        )
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_owner_can_download_when_finalizada(tmp_path: object) -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    actor = make_user(
        matricula="P6", email="p6@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    batch = make_respuesta(
        solicitud=sol, actor=actor, actor_role=Role.CONTROL_ESCOLAR
    )
    # Write a real file on the per-test MEDIA_ROOT so the FileResponse can stream it.
    from django.conf import settings
    from pathlib import Path

    rel = f"solicitudes/{sol.folio}/respuesta-bytes.pdf"
    p = Path(settings.MEDIA_ROOT) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-bytes")
    archivo = make_archivo_respuesta(
        respuesta=batch, stored_path=rel, nombre_original="firmada.pdf"
    )

    c = make_client(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.get(
        reverse(
            "solicitudes:respuesta:download",
            kwargs={
                "folio": sol.folio,
                "respuesta_id": batch.id,
                "archivo_id": archivo.id,
            },
        )
    )
    assert resp.status_code == 200
    assert b"".join(resp.streaming_content) == b"%PDF-bytes"


@pytest.mark.django_db
def test_other_alumno_cannot_download_even_finalizada() -> None:
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    actor = make_user(
        matricula="P7", email="p7@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    batch = make_respuesta(
        solicitud=sol, actor=actor, actor_role=Role.CONTROL_ESCOLAR
    )
    archivo = make_archivo_respuesta(respuesta=batch)
    make_user(matricula="A99", email="a99@uaz.edu.mx", role=Role.ALUMNO.value)
    c = make_client("A99", Role.ALUMNO)
    resp = c.get(
        reverse(
            "solicitudes:respuesta:download",
            kwargs={
                "folio": sol.folio,
                "respuesta_id": batch.id,
                "archivo_id": archivo.id,
            },
        )
    )
    assert resp.status_code == 403


# ---- Tier 1 integration: cross-feature personal → alumno flow --------


@pytest.mark.django_db
def test_personal_uploads_two_batches_and_finalizes_alumno_then_sees_responses() -> None:
    """Tier 1 integration: spans lifecycle (transition) + respuesta (upload/list)
    + intake detail (render). Personal in EN_PROCESO posts two batches, then
    finalizes; alumno views own detail and sees both batches.
    """
    tipo = _tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    make_user(matricula="P-INT", email="p-int@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    personal = make_client("P-INT", Role.CONTROL_ESCOLAR)

    # Batch 1
    r1 = personal.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={
            "comentario": "Borrador firmado",
            "archivos": [
                SimpleUploadedFile("draft.pdf", b"draft", content_type="application/pdf"),
            ],
        },
    )
    assert r1.status_code == 302

    # Batch 2
    r2 = personal.post(
        reverse("solicitudes:respuesta:create", kwargs={"folio": sol.folio}),
        data={
            "comentario": "Documento adicional",
            "archivos": [
                SimpleUploadedFile("anexo.pdf", b"anexo", content_type="application/pdf"),
            ],
        },
    )
    assert r2.status_code == 302
    assert RespuestaSolicitud.objects.filter(solicitud_id=sol.folio).count() == 2

    # Solicitante should not see batches yet (EN_PROCESO).
    alumno = make_client(sol.solicitante.matricula, Role.ALUMNO)
    resp_mid = alumno.get(
        reverse("solicitudes:intake:detail", kwargs={"folio": sol.folio})
    )
    assert resp_mid.status_code == 200
    assert resp_mid.context["respuestas"] == []
    assert b"Documentos de respuesta" not in resp_mid.content

    # Finalize via lifecycle.
    r3 = personal.post(
        reverse("solicitudes:revision:finalize", kwargs={"folio": sol.folio}),
        data={"observaciones": "Cerramos"},
    )
    assert r3.status_code in (302, 303)

    # Now alumno sees both batches with the response section visible.
    resp_post = alumno.get(
        reverse("solicitudes:intake:detail", kwargs={"folio": sol.folio})
    )
    assert resp_post.status_code == 200
    respuestas = resp_post.context["respuestas"]
    assert len(respuestas) == 2
    assert {r.comentario for r in respuestas} == {
        "Borrador firmado",
        "Documento adicional",
    }
    assert b"Documentos de respuesta" in resp_post.content
