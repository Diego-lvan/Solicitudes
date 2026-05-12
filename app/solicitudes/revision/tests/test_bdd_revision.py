"""BDD scenarios para la cola de revisión.

Cubre happy path (Control Escolar ve únicamente sus solicitudes) y alterno
(alumno recibe 403). Reusa los factories y la firma JWT del módulo
``test_revision_views.py``.
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

from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "revision-bdd-secret-32-bytes-long-aaaaaaa"
JWT_ALG = "HS256"

pytestmark = pytest.mark.django_db

scenarios("features/revision.feature")


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


@given(
    parsers.parse(
        'un tipo "{slug}" cuyo responsable es Control Escolar con una '
        'solicitud "{folio}"'
    )
)
def _ce_tipo(slug: str, folio: str) -> None:
    tipo = make_tipo(slug=slug, responsible_role=Role.CONTROL_ESCOLAR.value)
    make_solicitud(tipo=tipo, folio=folio)


@given(
    parsers.parse(
        'un tipo "{slug}" cuyo responsable es Responsable de Programa con una '
        'solicitud "{folio}"'
    )
)
def _rp_tipo(slug: str, folio: str) -> None:
    tipo = make_tipo(slug=slug, responsible_role=Role.RESPONSABLE_PROGRAMA.value)
    make_solicitud(tipo=tipo, folio=folio)


@given("un usuario de Control Escolar autenticado", target_fixture="cliente")
def _ce_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("CE1", Role.CONTROL_ESCOLAR)
    return c


@given("un alumno autenticado", target_fixture="cliente")
def _alumno_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU1", Role.ALUMNO)
    return c


# --- When ---------------------------------------------------------------


@when("consulta la cola de revisión")
@when("entra a la cola de revisión")
def _consultar_cola(ctx: dict[str, object], cliente: Client) -> None:
    ctx["resp"] = cliente.get(reverse("solicitudes:revision:queue"))


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_code(ctx: dict[str, object], code: int) -> None:
    assert ctx["resp"].status_code == code  # type: ignore[attr-defined,index]


@then(parsers.parse('la cola contiene el folio "{folio}"'))
def _then_lista_contiene(ctx: dict[str, object], folio: str) -> None:
    resp = ctx["resp"]
    folios = {r.folio for r in resp.context["page"].items}  # type: ignore[index]
    assert folio in folios


@then(parsers.parse('la cola no contiene el folio "{folio}"'))
def _then_lista_no_contiene(ctx: dict[str, object], folio: str) -> None:
    resp = ctx["resp"]
    folios = {r.folio for r in resp.context["page"].items}  # type: ignore[index]
    assert folio not in folios
