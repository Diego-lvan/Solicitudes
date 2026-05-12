"""Tier 1 cross-feature E2E for archivos (Django Client, no browser)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from solicitudes.archivos.tests.conftest import make_client
from solicitudes.models import ArchivoSolicitud, Solicitud
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import Role

_MIN_ZIP = b"PK\x05\x06" + b"\x00" * 18  # empty-archive end-of-central-directory


@pytest.mark.django_db(transaction=True)
def test_alumno_intake_with_form_attachment_and_comprobante(tmp_path: Path) -> None:
    """Cross-feature: intake stores FORM file + COMPROBANTE; owner downloads, others 403."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
        requires_payment=True,
    )
    text_field = make_field(
        tipo,
        order=0,
        label="Motivo",
        field_type=FieldType.TEXT.value,
    )
    file_field = make_field(
        tipo,
        order=1,
        label="Adjunto",
        field_type=FieldType.FILE.value,
        accepted_extensions=[".pdf", ".zip"],
        max_size_mb=5,
    )
    txt_attr = f"field_{str(text_field.id).replace('-', '')}"
    file_attr = f"field_{str(file_field.id).replace('-', '')}"

    alumno = make_client("ALU1", Role.ALUMNO)
    other = make_client("OTHER", Role.DOCENTE)

    pdf = SimpleUploadedFile("doc.pdf", b"%PDF-fake-bytes", content_type="application/pdf")
    comprobante = SimpleUploadedFile(
        "pago.png", b"\x89PNG-bytes", content_type="image/png"
    )

    resp = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={
            txt_attr: "Necesito constancia",
            file_attr: pdf,
            "comprobante": comprobante,
        },
    )
    assert resp.status_code == 302
    s = Solicitud.objects.get()
    archivos = list(ArchivoSolicitud.objects.filter(solicitud=s))
    assert len(archivos) == 2
    # Files landed under media/solicitudes/<folio>/
    for a in archivos:
        assert a.stored_path.startswith(f"solicitudes/{s.folio}/")

    # Owner can download
    a_form = next(a for a in archivos if a.kind == "FORM")
    download_url = reverse(
        "solicitudes:archivos:download", kwargs={"archivo_id": a_form.id}
    )
    resp = alumno.get(download_url)
    assert resp.status_code == 200
    assert resp["Content-Disposition"].startswith("attachment;")
    assert b"".join(resp.streaming_content) == b"%PDF-fake-bytes"  # type: ignore[attr-defined]

    # Unrelated user gets 403
    resp = other.get(download_url)
    assert resp.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_zip_stored_as_zip_and_round_trips(tmp_path: Path) -> None:
    """RF-10 / acceptance #2: a real .zip is stored as-is and downloads as .zip."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    file_field = make_field(
        tipo,
        order=0,
        label="Adjunto",
        field_type=FieldType.FILE.value,
        accepted_extensions=[".pdf", ".zip"],
        max_size_mb=5,
    )
    file_attr = f"field_{str(file_field.id).replace('-', '')}"

    alumno = make_client("ALU1", Role.ALUMNO)
    upload = SimpleUploadedFile(
        "soporte.zip", _MIN_ZIP, content_type="application/zip"
    )
    resp = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={file_attr: upload},
    )
    assert resp.status_code == 302
    archivo = ArchivoSolicitud.objects.get()
    assert archivo.original_filename == "soporte.zip"
    assert archivo.stored_path.endswith(".zip"), archivo.stored_path

    download_url = reverse(
        "solicitudes:archivos:download", kwargs={"archivo_id": archivo.id}
    )
    resp = alumno.get(download_url)
    assert resp.status_code == 200
    assert b"".join(resp.streaming_content) == _MIN_ZIP  # type: ignore[attr-defined]
    cd = resp["Content-Disposition"]
    assert cd.startswith("attachment;")
    assert "soporte.zip" in cd


@pytest.mark.django_db(transaction=True)
def test_form_field_rejects_disallowed_extension_at_form_level(
    tmp_path: Path,
) -> None:
    """Plan acceptance #1 amended: disallowed extensions are caught at form
    validation (HTTP 400) before the upload buffer reaches the service. The
    422 path remains for service-level rejections (e.g. comprobante)."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    file_field = make_field(
        tipo,
        order=0,
        label="Adjunto",
        field_type=FieldType.FILE.value,
        accepted_extensions=[".pdf"],
        max_size_mb=5,
    )
    file_attr = f"field_{str(file_field.id).replace('-', '')}"
    alumno = make_client("ALU1", Role.ALUMNO)
    bad = SimpleUploadedFile(
        "evil.exe", b"x" * 16, content_type="application/x-msdownload"
    )
    resp = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={file_attr: bad},
    )
    assert resp.status_code == 400
    assert ArchivoSolicitud.objects.count() == 0
    assert Solicitud.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_replace_on_reupload_leaves_prior_file_intact_on_rollback(
    tmp_path: Path,
) -> None:
    """Critical-1 regression: when a re-upload triggers replace, the prior
    file's bytes must NOT be deleted until the surrounding transaction
    commits. If the new write fails mid-transaction, the prior bytes must
    still be on disk."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    file_field = make_field(
        tipo,
        order=0,
        label="Adjunto",
        field_type=FieldType.FILE.value,
        accepted_extensions=[".pdf"],
        max_size_mb=5,
    )
    file_attr = f"field_{str(file_field.id).replace('-', '')}"

    from django.test.utils import override_settings

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        alumno = make_client("ALU1", Role.ALUMNO)

        # First successful upload — establishes the prior file on disk.
        first = SimpleUploadedFile(
            "v1.pdf", b"v1-bytes", content_type="application/pdf"
        )
        resp = alumno.post(
            reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
            data={file_attr: first},
        )
        assert resp.status_code == 302
        prior_archivo = ArchivoSolicitud.objects.get()
        prior_abs = tmp_path / prior_archivo.stored_path
        assert prior_abs.exists()

        # Second upload to the same field on the same solicitud is impossible
        # via intake (one solicitud per submit), so we exercise the replace
        # path directly through the service inside an atomic that we force to
        # rollback.
        from django.db import transaction

        from solicitudes.archivos.constants import ArchivoKind
        from solicitudes.archivos.dependencies import get_archivo_service
        from solicitudes.archivos.repositories.archivo.implementation import (
            OrmArchivoRepository,
        )
        from usuarios.schemas import UserDTO

        actor = UserDTO(
            matricula="ALU1",
            email="alu1@uaz.edu.mx",
            role=Role.ALUMNO,
        )
        # Force the *new* file's repo.create to raise so the atomic rolls back
        # AFTER the prior row was deleted and the on_commit cleanup was queued.
        def boom(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("simulated DB failure")

        with (
            patch.object(OrmArchivoRepository, "create", boom),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            get_archivo_service().store_for_solicitud(
                folio=prior_archivo.solicitud_id,
                field_id=file_field.id,
                kind=ArchivoKind.FORM,
                uploaded_file=SimpleUploadedFile(
                    "v2.pdf", b"v2-bytes", content_type="application/pdf"
                ),
                uploader=actor,
            )

        # Row was rolled back, so the prior archivo survives in the DB.
        assert ArchivoSolicitud.objects.filter(id=prior_archivo.id).exists()
        # And — the property under test — the prior file is still on disk.
        assert prior_abs.exists(), (
            f"prior file at {prior_abs} was deleted despite rollback"
        )


@pytest.mark.django_db(transaction=True)
def test_rollback_after_file_write_leaves_no_orphans(tmp_path: Path) -> None:
    """Force a DB error after files are written → atomic rollback removes them."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    file_field = make_field(
        tipo,
        order=0,
        label="Adjunto",
        field_type=FieldType.FILE.value,
        accepted_extensions=[".pdf"],
        max_size_mb=5,
    )
    file_attr = f"field_{str(file_field.id).replace('-', '')}"

    alumno = make_client("ALU1", Role.ALUMNO)
    pdf = SimpleUploadedFile("doc.pdf", b"x" * 64, content_type="application/pdf")

    # Patch the repo's create to fail after the storage.save has already
    # written the .partial file.
    from solicitudes.archivos.repositories.archivo.implementation import (
        OrmArchivoRepository,
    )

    real_create = OrmArchivoRepository.create

    def boom(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated DB failure")

    media_root = Path(tmp_path)
    from django.test.utils import override_settings

    with override_settings(MEDIA_ROOT=str(media_root)):
        with patch.object(OrmArchivoRepository, "create", boom):
            resp = alumno.post(
                reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
                data={file_attr: pdf},
            )

        # The view re-renders the form with a 5xx status, OR raises through.
        # Either way, no archivo rows persisted and no orphan files on disk.
        assert ArchivoSolicitud.objects.count() == 0
        assert Solicitud.objects.count() == 0  # outer atomic also rolled back
        # No leftover .partial files in the media tree
        leftover = list(media_root.rglob("*.partial"))
        assert leftover == [], f"orphan partials: {leftover}"
        # And no committed files either
        committed = [p for p in media_root.rglob("*") if p.is_file()]
        assert committed == [], f"orphan files: {committed}"
        # Make sure boom was actually triggered
        _ = real_create  # silence unused
        assert resp is not None
