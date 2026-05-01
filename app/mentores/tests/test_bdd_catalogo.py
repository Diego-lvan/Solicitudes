"""BDD scenarios for the mentores admin catalog (CSV import + auth).

Drives the same import-csv flow as ``test_views.py`` through Django's test
``Client``: happy path with valid + invalid rows, bad-header rejection, and
authorization gate against non-admin users.
"""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from pytest_bdd import given, parsers, scenarios, then, when

from mentores.tests.factories import make_admin_user
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "mentores-bdd-test-secret-32-bytes-long-aaa"
JWT_ALG = "HS256"

pytestmark = pytest.mark.django_db

scenarios("features/catalogo.feature")


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
def _given_admin() -> Client:
    make_admin_user(matricula="ADMIN1", email="admin1@uaz.edu.mx")
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    return c


@given("un usuario alumno autenticado", target_fixture="alumno_client")
def _given_alumno() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("A1", Role.ALUMNO)
    return c


# --- When ---------------------------------------------------------------


@when(
    parsers.parse(
        'el administrador sube un CSV con encabezado "{header}" y filas "{rows}"'
    )
)
def _when_admin_uploads(
    ctx: dict[str, object], admin_client: Client, header: str, rows: str
) -> None:
    body = header + "\n" + "\n".join(rows.split("|")) + "\n"
    payload = SimpleUploadedFile(
        "mentores.csv",
        body.encode("utf-8"),
        content_type="text/csv",
    )
    ctx["resp"] = admin_client.post(
        reverse("mentores:import_csv"), {"archivo": payload}
    )


@when("el alumno consulta la pantalla de importación CSV")
def _when_alumno_consulta(
    ctx: dict[str, object], alumno_client: Client
) -> None:
    ctx["resp"] = alumno_client.get(reverse("mentores:import_csv"))


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_status(ctx: dict[str, object], code: int) -> None:
    resp = ctx["resp"]
    assert resp.status_code == code, resp.content[:300]  # type: ignore[attr-defined]


@then(parsers.parse("el resumen reporta {n:d} filas totales"))
def _then_total_rows(ctx: dict[str, object], n: int) -> None:
    resp = ctx["resp"]
    assert resp.context["result"].total_rows == n  # type: ignore[index]


@then(parsers.parse("el resumen reporta {n:d} filas insertadas"))
def _then_inserted(ctx: dict[str, object], n: int) -> None:
    resp = ctx["resp"]
    assert resp.context["result"].inserted == n  # type: ignore[index]


@then(parsers.parse("el resumen reporta {n:d} fila inválida"))
@then(parsers.parse("el resumen reporta {n:d} filas inválidas"))
def _then_invalid(ctx: dict[str, object], n: int) -> None:
    resp = ctx["resp"]
    assert len(resp.context["result"].invalid_rows) == n  # type: ignore[index]


@then(parsers.parse('el formulario muestra error en el campo "{campo}"'))
def _then_form_error(ctx: dict[str, object], campo: str) -> None:
    resp = ctx["resp"]
    form = resp.context["form"]  # type: ignore[index]
    assert form.errors[campo]
