"""BDD scenarios for the reportes dashboard + CSV export.

Drives the same admin-only flows as ``test_views.py`` through Django's test
``Client``: dashboard rendering, date-range filtering, and CSV export with
BOM + filtered rows.
"""
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
from pytest_bdd import given, parsers, scenarios, then, when

from mentores.tests.factories import make_admin_user
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import Solicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "reportes-bdd-test-secret-32-bytes-long-aaa"
JWT_ALG = "HS256"

pytestmark = pytest.mark.django_db

scenarios("features/dashboard.feature")


@pytest.fixture(autouse=True)
def _jwt_settings() -> Iterator[None]:
    with override_settings(
        JWT_SECRET=JWT_SECRET,
        JWT_ALGORITHM=JWT_ALG,
        ALLOWED_HOSTS=["testserver"],
        SIGA_BASE_URL="",
    ):
        yield


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


@pytest.fixture
def ctx() -> dict[str, object]:
    return {}


# --- Antecedentes -------------------------------------------------------


@given("un usuario administrador autenticado", target_fixture="admin_client")
def _given_admin_authenticated() -> Client:
    make_admin_user(matricula="ADMIN1", email="admin1@uaz.edu.mx")
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    return c


@given(
    parsers.parse(
        'dos solicitudes en estado CREADA del tipo "{nombre}"'
    )
)
def _given_two_creadas(ctx: dict[str, object], nombre: str) -> None:
    tipo = make_tipo(slug="tipo-bdd", nombre=nombre)
    make_solicitud(tipo=tipo, estado=Estado.CREADA)
    make_solicitud(tipo=tipo, estado=Estado.CREADA)
    ctx["tipo"] = tipo


@given(
    parsers.parse(
        'una solicitud en estado FINALIZADA del tipo "{nombre}"'
    )
)
def _given_one_finalizada(ctx: dict[str, object], nombre: str) -> None:
    tipo = ctx.get("tipo")
    if tipo is None:
        tipo = make_tipo(slug="tipo-bdd-fin", nombre=nombre)
        ctx["tipo"] = tipo
    make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)


@given(parsers.parse('una solicitud creada el "{date_iso}"'))
def _given_solicitud_dated(ctx: dict[str, object], date_iso: str) -> None:
    tipo = ctx.get("tipo")
    if tipo is None:
        tipo = make_tipo(slug="tipo-dated", nombre="Tipo fechado")
        ctx["tipo"] = tipo
    s = make_solicitud(tipo=tipo)
    when = datetime.fromisoformat(date_iso).replace(tzinfo=UTC)
    Solicitud.objects.filter(pk=s.folio).update(created_at=when)


# --- When ---------------------------------------------------------------


@when("el administrador abre el dashboard")
def _when_open_dashboard(ctx: dict[str, object], admin_client: Client) -> None:
    ctx["resp"] = admin_client.get(reverse("reportes:dashboard"))


@when(
    parsers.parse(
        'el administrador abre el dashboard con el filtro "{ini}" a "{fin}"'
    )
)
def _when_open_dashboard_filtered(
    ctx: dict[str, object], admin_client: Client, ini: str, fin: str
) -> None:
    ctx["resp"] = admin_client.get(
        reverse("reportes:dashboard")
        + f"?created_from={ini}&created_to={fin}"
    )


@when(
    parsers.parse(
        'el administrador exporta el reporte en CSV con estado "{estado}"'
    )
)
def _when_export_csv(
    ctx: dict[str, object], admin_client: Client, estado: str
) -> None:
    ctx["resp"] = admin_client.get(
        reverse("reportes:export_csv") + f"?estado={estado}"
    )


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_status(ctx: dict[str, object], code: int) -> None:
    resp = ctx["resp"]
    assert resp.status_code == code, resp.content[:300]  # type: ignore[attr-defined]


@then(parsers.parse('el dashboard muestra "{needle}"'))
def _then_dashboard_shows(ctx: dict[str, object], needle: str) -> None:
    resp = ctx["resp"]
    assert needle.encode("utf-8") in resp.content  # type: ignore[attr-defined]


@then(parsers.parse("el total del dashboard es {n:d}"))
def _then_dashboard_total(ctx: dict[str, object], n: int) -> None:
    resp = ctx["resp"]
    assert resp.context["dashboard"].total == n  # type: ignore[attr-defined]


@then(parsers.parse('el Content-Type del CSV es "{ct}"'))
def _then_content_type(ctx: dict[str, object], ct: str) -> None:
    resp = ctx["resp"]
    assert resp["Content-Type"].startswith(ct)  # type: ignore[index]


@then("el archivo CSV inicia con BOM UTF-8")
def _then_csv_bom(ctx: dict[str, object]) -> None:
    resp = ctx["resp"]
    assert resp.content.startswith(b"\xef\xbb\xbf")  # type: ignore[attr-defined]


@then(parsers.parse("el CSV tiene exactamente {n:d} filas"))
def _then_csv_rows(ctx: dict[str, object], n: int) -> None:
    resp = ctx["resp"]
    text = resp.content.decode("utf-8-sig")  # type: ignore[attr-defined]
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == n, rows
