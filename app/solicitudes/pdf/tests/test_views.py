"""View tests for plantilla CRUD + the per-solicitud PDF download endpoint."""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import PlantillaSolicitud
from solicitudes.pdf.tests.factories import make_plantilla
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.tests.factories import make_user

JWT_SECRET = "pdf-views-test-secret-32-bytes-long-aa"
JWT_ALG = "HS256"


def _mint(matricula: str, role: Role) -> str:
    return jwt.encode(
        {
            "sub": matricula,
            "email": f"{matricula.lower()}@uaz.edu.mx",
            "rol": role.value.lower(),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


@pytest.fixture(autouse=True)
def _jwt_settings() -> Iterator[None]:
    with override_settings(
        JWT_SECRET=JWT_SECRET,
        JWT_ALGORITHM=JWT_ALG,
        ALLOWED_HOSTS=["testserver"],
        SIGA_BASE_URL="",
    ):
        yield


def _client_for(matricula: str, role: Role) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint(matricula, role)
    return c


@pytest.fixture
def admin_client() -> Client:
    return _client_for("ADMIN1", Role.ADMIN)


@pytest.fixture
def alumno_client() -> Client:
    return _client_for("A1", Role.ALUMNO)


# ---------- plantilla CRUD admin views ----------


@pytest.mark.django_db
def test_admin_can_list_plantillas(admin_client: Client) -> None:
    make_plantilla(nombre="P1")
    resp = admin_client.get(reverse("solicitudes:plantillas:list"))
    assert resp.status_code == 200
    assert "plantillas" in resp.context


@pytest.mark.django_db
def test_alumno_cannot_list_plantillas(alumno_client: Client) -> None:
    resp = alumno_client.get(reverse("solicitudes:plantillas:list"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_create_persists_plantilla(admin_client: Client) -> None:
    resp = admin_client.post(
        reverse("solicitudes:plantillas:create"),
        data={
            "nombre": "Constancia",
            "descripcion": "d",
            "html": "<p>{{ solicitante.nombre }}</p>",
            "css": "",
            "activo": "on",
        },
    )
    assert resp.status_code == 302
    assert PlantillaSolicitud.objects.filter(nombre="Constancia").exists()


@pytest.mark.django_db
def test_admin_create_rejects_invalid_template(admin_client: Client) -> None:
    resp = admin_client.post(
        reverse("solicitudes:plantillas:create"),
        data={
            "nombre": "Bad",
            "descripcion": "",
            "html": "<p>{% if x %}</p>",  # unclosed
            "css": "",
            "activo": "on",
        },
    )
    assert resp.status_code == 422
    assert PlantillaSolicitud.objects.count() == 0


@pytest.mark.django_db
def test_admin_edit_updates_plantilla(admin_client: Client) -> None:
    p = make_plantilla(nombre="Old")
    resp = admin_client.post(
        reverse("solicitudes:plantillas:edit", kwargs={"plantilla_id": p.id}),
        data={
            "nombre": "Renombrada",
            "descripcion": "",
            "html": "<p>x</p>",
            "css": "",
            "activo": "on",
        },
    )
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.nombre == "Renombrada"


# ---------- PDF download view ----------


@pytest.mark.django_db
def test_owner_downloads_pdf_when_finalizada() -> None:
    tipo = make_tipo()
    plantilla = make_plantilla()
    tipo.plantilla = plantilla
    tipo.save()
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)

    c = _client_for(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.get(reverse("solicitudes:pdf_download", kwargs={"folio": sol.folio}))

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert sol.folio in resp["Content-Disposition"]


@pytest.mark.django_db
def test_owner_pre_finalizada_gets_403() -> None:
    tipo = make_tipo()
    plantilla = make_plantilla()
    tipo.plantilla = plantilla
    tipo.save()
    sol = make_solicitud(tipo=tipo, estado=Estado.CREADA)

    c = _client_for(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.get(reverse("solicitudes:pdf_download", kwargs={"folio": sol.folio}))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_no_plantilla_returns_409() -> None:
    tipo = make_tipo()  # tipo.plantilla = None
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    c = _client_for(sol.solicitante.matricula, Role.ALUMNO)
    resp = c.get(reverse("solicitudes:pdf_download", kwargs={"folio": sol.folio}))
    assert resp.status_code == 409


@pytest.mark.django_db
def test_personal_can_download_at_any_estado() -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    plantilla = make_plantilla()
    tipo.plantilla = plantilla
    tipo.save()
    sol = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    make_user(matricula="P1", email="p1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    c = _client_for("P1", Role.CONTROL_ESCOLAR)
    resp = c.get(reverse("solicitudes:pdf_download", kwargs={"folio": sol.folio}))
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_admin_can_preview_plantilla(admin_client: Client) -> None:
    p = make_plantilla()
    resp = admin_client.get(
        reverse("solicitudes:plantillas:preview", kwargs={"plantilla_id": p.id})
    )
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp["Content-Disposition"].startswith("inline;")
    assert resp.content.startswith(b"%PDF")
    # The detail template embeds this URL in an <iframe>; SAMEORIGIN must
    # stay in place or the iframe silently blanks under Django's default
    # X-Frame-Options: DENY.
    assert resp["X-Frame-Options"].upper() == "SAMEORIGIN"


@pytest.mark.django_db
def test_alumno_cannot_preview_plantilla(alumno_client: Client) -> None:
    p = make_plantilla()
    resp = alumno_client.get(
        reverse("solicitudes:plantillas:preview", kwargs={"plantilla_id": p.id})
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_anonymous_redirected_or_401() -> None:
    tipo = make_tipo()
    plantilla = make_plantilla()
    tipo.plantilla = plantilla
    tipo.save()
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    resp = Client().get(reverse("solicitudes:pdf_download", kwargs={"folio": sol.folio}))
    # AppErrorMiddleware turns AuthenticationRequired into a redirect to login,
    # not a 200. Either 302 (redirect) or 401 is acceptable.
    assert resp.status_code in (302, 401)
