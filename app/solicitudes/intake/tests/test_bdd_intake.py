"""BDD scenarios for the intake catalog (alta de solicitudes desde el alumno).

Reuses the factories from ``solicitudes.tipos.tests`` and the Django ``Client``
with a JWT cookie, mirroring how ``test_intake_views.py`` already drives the
catalog view. Two scenarios: happy (alumno ve el catálogo) y alterno (sin
sesión queda bloqueado).
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

from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.tests.factories import make_user

JWT_SECRET = "intake-bdd-test-secret-32-bytes-long-aaaa"
JWT_ALG = "HS256"

pytestmark = pytest.mark.django_db

scenarios("features/intake.feature")


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


@given(parsers.parse('existe un tipo de solicitud "{slug}" activo para rol alumno'))
def _tipo_activo(slug: str) -> None:
    make_tipo(slug=slug, nombre=slug.replace("-", " ").title(), activo=True)


# --- Given --------------------------------------------------------------


@given(
    parsers.parse('un alumno autenticado con matrícula "{matricula}"'),
    target_fixture="cliente",
)
def _alumno(matricula: str) -> Client:
    make_user(matricula=matricula, role=Role.ALUMNO)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint(matricula, Role.ALUMNO)
    return c


@given("un visitante sin sesión iniciada", target_fixture="cliente")
def _anon() -> Client:
    return Client()


# --- When ---------------------------------------------------------------


@when("el alumno entra al catálogo de solicitudes")
@when("entra al catálogo de solicitudes")
def _entrar_catalogo(ctx: dict[str, object], cliente: Client) -> None:
    ctx["resp"] = cliente.get(reverse("solicitudes:intake:catalog"))


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_code(ctx: dict[str, object], code: int) -> None:
    assert ctx["resp"].status_code == code, ctx["resp"].content[:200]  # type: ignore[attr-defined,index]


@then("la respuesta no es 200")
def _then_not_200(ctx: dict[str, object]) -> None:
    assert ctx["resp"].status_code != 200  # type: ignore[attr-defined,index]


@then(parsers.parse('el catálogo lista el tipo "{slug}"'))
def _then_lista_tipo(ctx: dict[str, object], slug: str) -> None:
    resp = ctx["resp"]
    body = resp.content.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
    assert slug in body or slug.replace("-", " ").title() in body
