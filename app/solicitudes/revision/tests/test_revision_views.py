"""Revision view tests — queue, detail, take, finalize, cancel."""
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
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.tests.factories import make_user

JWT_SECRET = "revision-views-test-secret-32-bytes-long"
JWT_ALG = "HS256"


_INTERNAL_TO_PROVIDER = {
    Role.ALUMNO: "alumno",
    Role.DOCENTE: "docente",
    Role.CONTROL_ESCOLAR: "control_escolar",
    Role.RESPONSABLE_PROGRAMA: "resp_programa",
    Role.ADMIN: "admin",
}


def _mint(matricula: str, role: Role) -> str:
    return jwt.encode(
        {
            "sub": matricula,
            "email": f"{matricula.lower()}@uaz.edu.mx",
            "rol": _INTERNAL_TO_PROVIDER[role],
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


@pytest.fixture
def ce_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("CE1", Role.CONTROL_ESCOLAR)
    return c


@pytest.fixture
def rp_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("RP1", Role.RESPONSABLE_PROGRAMA)
    return c


@pytest.fixture
def admin_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADM1", Role.ADMIN)
    return c


@pytest.fixture
def alumno_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU1", Role.ALUMNO)
    return c


# ---- queue ----


@pytest.mark.django_db
def test_queue_lists_only_role_scoped_solicitudes(ce_client: Client) -> None:
    tipo_ce = make_tipo(slug="ce-tipo", responsible_role=Role.CONTROL_ESCOLAR.value)
    tipo_rp = make_tipo(slug="rp-tipo", responsible_role=Role.RESPONSABLE_PROGRAMA.value)
    make_solicitud(tipo=tipo_ce, folio="SOL-2026-00001")
    make_solicitud(tipo=tipo_rp, folio="SOL-2026-00002")
    response = ce_client.get(reverse("solicitudes:revision:queue"))
    assert response.status_code == 200
    folios = {r.folio for r in response.context["page"].items}
    assert folios == {"SOL-2026-00001"}


@pytest.mark.django_db
def test_queue_admin_sees_all(admin_client: Client) -> None:
    tipo_ce = make_tipo(slug="ce-tipo", responsible_role=Role.CONTROL_ESCOLAR.value)
    tipo_rp = make_tipo(slug="rp-tipo", responsible_role=Role.RESPONSABLE_PROGRAMA.value)
    make_solicitud(tipo=tipo_ce, folio="SOL-2026-00001")
    make_solicitud(tipo=tipo_rp, folio="SOL-2026-00002")
    response = admin_client.get(reverse("solicitudes:revision:queue"))
    assert response.status_code == 200
    assert response.context["page"].total == 2


@pytest.mark.django_db
def test_queue_rejects_alumno(alumno_client: Client) -> None:
    response = alumno_client.get(reverse("solicitudes:revision:queue"))
    assert response.status_code == 403


# ---- detail ----


@pytest.mark.django_db
def test_detail_shows_role_scoped_solicitud(ce_client: Client) -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo)
    response = ce_client.get(
        reverse("solicitudes:revision:detail", kwargs={"folio": s.folio})
    )
    assert response.status_code == 200
    assert response.context["detail"].folio == s.folio


@pytest.mark.django_db
def test_detail_role_mismatch_rejected(rp_client: Client) -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo)
    response = rp_client.get(
        reverse("solicitudes:revision:detail", kwargs={"folio": s.folio})
    )
    assert response.status_code == 403


# ---- transitions ----


@pytest.mark.django_db
def test_atender_moves_to_en_proceso(ce_client: Client) -> None:
    make_user(matricula="CE1", email="ce1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    response = ce_client.post(
        reverse("solicitudes:revision:take", kwargs={"folio": s.folio})
    )
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.EN_PROCESO.value


@pytest.mark.django_db
def test_finalizar_moves_to_finalizada(ce_client: Client) -> None:
    make_user(matricula="CE1", email="ce1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    response = ce_client.post(
        reverse("solicitudes:revision:finalize", kwargs={"folio": s.folio})
    )
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.FINALIZADA.value


@pytest.mark.django_db
def test_finalizar_from_creada_blocked(ce_client: Client) -> None:
    make_user(matricula="CE1", email="ce1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    response = ce_client.post(
        reverse("solicitudes:revision:finalize", kwargs={"folio": s.folio})
    )
    # AppError → flash + redirect.
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.CREADA.value


@pytest.mark.django_db
def test_cancel_by_personal_succeeds(ce_client: Client) -> None:
    make_user(matricula="CE1", email="ce1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    response = ce_client.post(
        reverse("solicitudes:revision:cancel", kwargs={"folio": s.folio})
    )
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.CANCELADA.value


@pytest.mark.django_db
def test_atender_unauthorized_when_role_mismatch(rp_client: Client) -> None:
    make_user(matricula="RP1", email="rp1@uaz.edu.mx", role=Role.RESPONSABLE_PROGRAMA.value)
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    s = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    response = rp_client.post(
        reverse("solicitudes:revision:take", kwargs={"folio": s.folio})
    )
    # Either redirect (caught AppError) or 403 — either is acceptable.
    assert response.status_code in (302, 403)
    s.refresh_from_db()
    assert s.estado == Estado.CREADA.value
