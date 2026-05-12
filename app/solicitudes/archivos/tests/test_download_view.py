"""Download view auth-matrix tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from solicitudes.archivos.tests.conftest import make_client
from solicitudes.archivos.tests.factories import make_archivo
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import ArchivoSolicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.tests.factories import make_user


def _materialize_archivo(archivo: ArchivoSolicitud) -> None:
    """Drop a file at the model's stored_path so the view can stream it."""
    abs_path = Path(settings.MEDIA_ROOT) / archivo.stored_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(b"file-bytes")


@pytest.mark.django_db
def test_owner_can_download() -> None:
    user = make_user(matricula="ALU-OWN", email="own@uaz.edu.mx", role=Role.ALUMNO.value)
    solicitud = make_solicitud(solicitante=user)
    archivo = make_archivo(solicitud=solicitud)
    _materialize_archivo(archivo)

    client = make_client("ALU-OWN", Role.ALUMNO)
    url = reverse("solicitudes:archivos:download", kwargs={"archivo_id": archivo.id})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b"".join(resp.streaming_content) == b"file-bytes"  # type: ignore[attr-defined]
    assert resp["Content-Disposition"].startswith("attachment;")
    assert "doc.pdf" in resp["Content-Disposition"]


@pytest.mark.django_db
def test_responsible_role_can_download() -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    solicitud = make_solicitud(tipo=tipo)
    archivo = make_archivo(solicitud=solicitud)
    _materialize_archivo(archivo)

    client = make_client("CE1", Role.CONTROL_ESCOLAR)
    url = reverse("solicitudes:archivos:download", kwargs={"archivo_id": archivo.id})
    resp = client.get(url)

    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_can_download() -> None:
    archivo = make_archivo()
    _materialize_archivo(archivo)
    client = make_client("ADM1", Role.ADMIN)
    url = reverse("solicitudes:archivos:download", kwargs={"archivo_id": archivo.id})
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_unrelated_user_gets_403() -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    solicitud = make_solicitud(tipo=tipo)  # solicitante is some random ALU
    archivo = make_archivo(solicitud=solicitud)
    _materialize_archivo(archivo)

    client = make_client("OTHER", Role.DOCENTE)
    url = reverse("solicitudes:archivos:download", kwargs={"archivo_id": archivo.id})
    resp = client.get(url)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unknown_archivo_returns_404() -> None:
    from uuid import uuid4

    client = make_client("ADM1", Role.ADMIN)
    url = reverse(
        "solicitudes:archivos:download", kwargs={"archivo_id": uuid4()}
    )
    resp = client.get(url)
    assert resp.status_code == 404
