"""View tests for reportes — admin-only access + Tier 1 cross-feature E2E."""
from __future__ import annotations

import csv
import io
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from mentores.tests.factories import make_admin_user
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import Solicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.tests.factories import make_user

JWT_SECRET = "reportes-views-test-secret-32-bytes-long-aaa"
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


@pytest.fixture
def admin_client() -> Client:
    make_admin_user(matricula="ADMIN1", email="admin1@uaz.edu.mx")
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    return c


@pytest.fixture
def alumno_client() -> Client:
    make_user(matricula="ALU1", email="alu1@uaz.edu.mx", role=Role.ALUMNO.value)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU1", Role.ALUMNO)
    return c


def _set_created(s: Solicitud, when: datetime) -> None:
    Solicitud.objects.filter(pk=s.folio).update(created_at=when)


@pytest.mark.django_db
def test_dashboard_returns_403_for_non_admin(alumno_client: Client) -> None:
    resp = alumno_client.get(reverse("reportes:dashboard"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dashboard_returns_200_and_renders_counts_for_admin(
    admin_client: Client,
) -> None:
    tipo_a = make_tipo(slug="tipo-a", nombre="Constancia académica")
    make_solicitud(tipo=tipo_a, estado=Estado.CREADA)
    make_solicitud(tipo=tipo_a, estado=Estado.CREADA)
    make_solicitud(tipo=tipo_a, estado=Estado.FINALIZADA)

    resp = admin_client.get(reverse("reportes:dashboard"))
    assert resp.status_code == 200
    assert b"Reportes" in resp.content
    assert b"Constancia" in resp.content


@pytest.mark.django_db
def test_dashboard_date_range_filter_narrows_counts(
    admin_client: Client,
) -> None:
    tipo = make_tipo()
    in_range = make_solicitud(tipo=tipo)
    out_of_range = make_solicitud(tipo=tipo)
    _set_created(in_range, datetime(2026, 4, 10, 12, tzinfo=UTC))
    _set_created(out_of_range, datetime(2025, 1, 10, 12, tzinfo=UTC))

    resp = admin_client.get(
        reverse("reportes:dashboard")
        + "?created_from=2026-01-01&created_to=2026-12-31"
    )
    assert resp.status_code == 200
    dashboard = resp.context["dashboard"]
    assert dashboard.total == 1


@pytest.mark.django_db
def test_csv_export_admin_returns_text_csv_with_bom_and_filtered_rows(
    admin_client: Client,
) -> None:
    tipo_a = make_tipo(slug="tipo-a", nombre="Constancia académica")
    tipo_b = make_tipo(slug="tipo-b", nombre="Beca")
    make_solicitud(tipo=tipo_a, estado=Estado.CREADA)
    make_solicitud(tipo=tipo_b, estado=Estado.FINALIZADA)

    resp = admin_client.get(
        reverse("reportes:export_csv") + "?estado=CREADA"
    )
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert resp["Content-Disposition"].startswith("attachment")
    body = resp.content
    assert body.startswith(b"\xef\xbb\xbf")
    text = body.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    # Header + 1 data row (only the CREADA solicitud passed the estado filter).
    assert len(rows) == 2
    # Spanish accents survive the round-trip.
    assert "Constancia académica" in rows[1]


@pytest.mark.django_db
def test_csv_export_returns_403_for_non_admin(alumno_client: Client) -> None:
    resp = alumno_client.get(reverse("reportes:export_csv"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_pdf_export_admin_returns_pdf_bytes(admin_client: Client) -> None:
    tipo = make_tipo()
    make_solicitud(tipo=tipo)

    resp = admin_client.get(reverse("reportes:export_pdf"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_dashboard_tipo_filter_marks_option_selected(
    admin_client: Client,
) -> None:
    """Regression: the Tipo dropdown re-marks the active UUID after submit."""
    tipo_a = make_tipo(slug="tipo-a", nombre="Constancia")
    tipo_b = make_tipo(slug="tipo-b", nombre="Beca")
    make_solicitud(tipo=tipo_a)
    make_solicitud(tipo=tipo_b)

    resp = admin_client.get(
        reverse("reportes:dashboard") + f"?tipo_id={tipo_a.id}"
    )
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    needle = f'value="{tipo_a.id}" selected'
    assert needle in body, "active Tipo option should carry `selected`"
    # And the other tipo must NOT be selected.
    other = f'value="{tipo_b.id}" selected'
    assert other not in body


@pytest.mark.django_db
def test_list_view_returns_200_and_renders_rows(admin_client: Client) -> None:
    tipo = make_tipo(slug="tipo-l", nombre="Constancia académica")
    make_solicitud(tipo=tipo, estado=Estado.CREADA)
    make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)

    resp = admin_client.get(reverse("reportes:list"))
    assert resp.status_code == 200
    page = resp.context["page"]
    assert page.total == 2
    # Spanish accents survive into the rendered cell.
    assert b"Constancia acad" in resp.content


@pytest.mark.django_db
def test_list_view_returns_403_for_non_admin(alumno_client: Client) -> None:
    resp = alumno_client.get(reverse("reportes:list"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_list_view_estado_filter_narrows(admin_client: Client) -> None:
    tipo = make_tipo()
    make_solicitud(tipo=tipo, estado=Estado.CREADA)
    make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)

    resp = admin_client.get(reverse("reportes:list") + "?estado=CREADA")
    assert resp.status_code == 200
    assert resp.context["page"].total == 1


@pytest.mark.django_db
def test_list_view_invalid_page_param_falls_back_to_page_1(
    admin_client: Client,
) -> None:
    """The view's `int(...)` guard catches non-numeric `page` values."""
    tipo = make_tipo()
    make_solicitud(tipo=tipo)
    resp = admin_client.get(reverse("reportes:list") + "?page=not-a-number")
    assert resp.status_code == 200
    assert resp.context["page"].page == 1


@pytest.mark.django_db
def test_dashboard_query_count_is_bounded(
    admin_client: Client, django_assert_max_num_queries
) -> None:
    tipo = make_tipo()
    for _ in range(3):
        make_solicitud(tipo=tipo)

    # 3 aggregate queries (estado, tipo, month — total is summed in Python from
    # by_estado, no extra query) + 1 tipo-list for the filter dropdown + auth
    # overhead (~7 queries: select/update/savepoints around `last_login_at`).
    # Tightened to the floor that passes today so an N+1 regression — say,
    # rendering one extra query per row in the per-tipo card — fails loudly.
    with django_assert_max_num_queries(12):
        admin_client.get(reverse("reportes:dashboard"))
