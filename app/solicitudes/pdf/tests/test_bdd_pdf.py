"""BDD scenarios para el catálogo de plantillas PDF en el panel admin.

Cubre happy path (admin ve el listado con la plantilla creada) y alterno
(alumno recibe 403 porque la vista usa ``AdminRequiredMixin``).
"""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from pytest_bdd import given, parsers, scenarios, then, when

from solicitudes.pdf.tests.factories import make_plantilla
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "pdf-bdd-secret-32-bytes-long-aaaaaaaaaaaa"
JWT_ALG = "HS256"

pytestmark = pytest.mark.django_db

scenarios("features/pdf.feature")


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


# --- Given --------------------------------------------------------------


@given(parsers.parse('existe una plantilla "{nombre}" activa'))
def _plantilla_activa(ctx: dict[str, object], nombre: str) -> None:
    make_plantilla(nombre=nombre, activo=True)
    ctx["nombre_plantilla"] = nombre


@given("un administrador autenticado", target_fixture="cliente")
def _admin() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADM1", Role.ADMIN)
    return c


@given("un alumno autenticado", target_fixture="cliente")
def _alumno() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU1", Role.ALUMNO)
    return c


# --- When ---------------------------------------------------------------


@when("el administrador entra al listado de plantillas")
@when("el alumno entra al listado de plantillas")
def _entrar_listado(ctx: dict[str, object], cliente: Client) -> None:
    ctx["resp"] = cliente.get(reverse("solicitudes:plantillas:list"))


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_code(ctx: dict[str, object], code: int) -> None:
    assert ctx["resp"].status_code == code  # type: ignore[attr-defined,index]


@then(parsers.parse('el listado incluye la plantilla "{nombre}"'))
def _then_listado_incluye(ctx: dict[str, object], nombre: str) -> None:
    resp = ctx["resp"]
    body = resp.content.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
    assert nombre in body
