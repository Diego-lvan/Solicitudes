"""View tests + Tier-1 in-process integration for the admin user directory.

Auth uses the real JWT middleware: mint a token, set the ``stk`` cookie, and
let the middleware materialize ``request.user`` — same pattern as the mentores
and reportes test suites.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from usuarios.constants import PROVIDER_ROLE_MAP, SESSION_COOKIE_NAME, Role
from usuarios.models import User
from usuarios.tests.factories import make_user

# Inverse of PROVIDER_ROLE_MAP — internal Role → provider claim string accepted
# by the role resolver. Required because ``Role.value.lower()`` does not match
# the provider's vocabulary for every role (e.g. RESPONSABLE_PROGRAMA →
# "resp_programa", not "responsable_programa").
_ROLE_TO_CLAIM: dict[Role, str] = {role: claim for claim, role in PROVIDER_ROLE_MAP.items()}

JWT_SECRET = "directory-views-test-secret-32-bytes-long-aaaa"
JWT_ALG = "HS256"


def _mint(matricula: str, role: Role) -> str:
    return jwt.encode(
        {
            "sub": matricula,
            "email": f"{matricula.lower()}@uaz.edu.mx",
            "rol": _ROLE_TO_CLAIM[role],
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
    ):
        yield


@pytest.fixture
def admin_user() -> User:
    return make_user(matricula="ADM1", role=Role.ADMIN.value, full_name="Admin Uno")


@pytest.fixture
def admin_client(admin_user: User) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint(admin_user.matricula, Role.ADMIN)
    return c


@pytest.fixture
def alumno_client() -> Client:
    make_user(matricula="ALU99", role=Role.ALUMNO.value)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU99", Role.ALUMNO)
    return c


@pytest.fixture
def docente_client() -> Client:
    make_user(matricula="DOC99", role=Role.DOCENTE.value)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("DOC99", Role.DOCENTE)
    return c


@pytest.fixture
def ce_client() -> Client:
    make_user(matricula="CE99", role=Role.CONTROL_ESCOLAR.value)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("CE99", Role.CONTROL_ESCOLAR)
    return c


@pytest.fixture
def rp_client() -> Client:
    make_user(matricula="RP99", role=Role.RESPONSABLE_PROGRAMA.value)
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("RP99", Role.RESPONSABLE_PROGRAMA)
    return c


# ---------------------------------------------------------------------------
# List view
# ---------------------------------------------------------------------------

LIST_URL = "/usuarios/"


@pytest.mark.django_db
def test_list_renders_for_admin(admin_client: Client, admin_user: User) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value, full_name="Ana")
    make_user(matricula="ALU02", role=Role.ALUMNO.value, full_name="Bruno")
    response = admin_client.get(LIST_URL)
    assert response.status_code == 200
    page = response.context["page"]
    assert {u.matricula for u in page.items} >= {"ADM1", "ALU01", "ALU02"}


@pytest.mark.django_db
def test_list_paginates_and_filters_by_role(
    admin_client: Client, admin_user: User
) -> None:
    # Need PAGE_SIZE+1 so pagination links appear.
    for i in range(28):
        make_user(matricula=f"ALU{i:02d}", role=Role.ALUMNO.value)
    make_user(matricula="DOC01", role=Role.DOCENTE.value)
    # Filter by role + page=2 => should land in page 2 of alumno-only set.
    response = admin_client.get(LIST_URL, {"role": "ALUMNO", "page": "2"})
    assert response.status_code == 200
    page = response.context["page"]
    assert page.page == 2
    assert page.total == 28  # only ALUMNO rows
    assert all(item.role is Role.ALUMNO for item in page.items)
    # Pagination links must carry the active filter QS.
    body = response.content.decode()
    assert "role=ALUMNO" in body
    assert "page=1" in body  # previous link


@pytest.mark.django_db
def test_list_q_search_matches_full_name(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="X1", role=Role.ALUMNO.value, full_name="Maximiliano Cruz")
    make_user(matricula="X2", role=Role.ALUMNO.value, full_name="Otra Persona")
    response = admin_client.get(LIST_URL, {"q": "max"})
    assert response.status_code == 200
    matriculas = {u.matricula for u in response.context["page"].items}
    assert matriculas == {"X1"}


@pytest.mark.django_db
def test_list_links_rows_to_detail_with_return_qs(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    response = admin_client.get(LIST_URL, {"role": "ALUMNO", "q": "alu"})
    body = response.content.decode()
    # The detail URL is present and the return QS is preserved (encoded).
    assert "/usuarios/ALU01/" in body
    assert "return=" in body
    assert "role%3DALUMNO" in body or "role=ALUMNO" in body


@pytest.mark.django_db
def test_list_empty_state_when_no_match(
    admin_client: Client, admin_user: User
) -> None:
    response = admin_client.get(LIST_URL, {"q": "no-such-user-anywhere"})
    assert response.status_code == 200
    assert "Sin coincidencias" in response.content.decode()


@pytest.mark.django_db
def test_list_permissive_parsing_bogus_role_and_page(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    response = admin_client.get(LIST_URL, {"role": "BOGUS", "page": "abc"})
    assert response.status_code == 200
    page = response.context["page"]
    assert page.page == 1
    # No role filter applied — admin user is also visible.
    assert "ADM1" in {u.matricula for u in page.items}


# ---------------------------------------------------------------------------
# Detail view — mentor overlay
# ---------------------------------------------------------------------------


def _patch_mentor(returns: bool | None = None, raises: Exception | None = None):
    target = "usuarios.directory.services.user_directory.implementation."
    target += "DefaultUserDirectoryService"

    def _is_mentor(self: Any, matricula: str) -> bool:  # noqa: ARG001
        if raises is not None:
            raise raises
        assert returns is not None
        return returns

    return patch(
        "mentores.services.mentor_service.implementation.DefaultMentorService.is_mentor",
        autospec=True,
        side_effect=lambda self, matricula: (
            (_ for _ in ()).throw(raises) if raises is not None else returns
        ),
    )


@pytest.mark.django_db
def test_detail_renders_with_is_mentor_true(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value, full_name="Ana")
    with _patch_mentor(returns=True):
        response = admin_client.get(f"/usuarios/ALU01/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Sí" in body
    assert "Está activo" in body


@pytest.mark.django_db
def test_detail_renders_with_is_mentor_false(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    with _patch_mentor(returns=False):
        response = admin_client.get(f"/usuarios/ALU01/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "No figura" in body


@pytest.mark.django_db
def test_detail_when_mentor_service_raises_renders_desconocido(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    with _patch_mentor(raises=RuntimeError("upstream boom")):
        response = admin_client.get(f"/usuarios/ALU01/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Desconocido" in body
    assert "no fue posible consultar" in body.lower()


@pytest.mark.django_db
def test_detail_back_link_uses_safe_return(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    with _patch_mentor(returns=False):
        response = admin_client.get(
            "/usuarios/ALU01/", {"return": "/usuarios/?role=ALUMNO"}
        )
    assert response.status_code == 200
    assert "/usuarios/?role=ALUMNO" in response.content.decode()


@pytest.mark.django_db
def test_detail_unsafe_return_falls_back_to_list(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    with _patch_mentor(returns=False):
        response = admin_client.get(
            "/usuarios/ALU01/", {"return": "https://evil.example.com/"}
        )
    assert response.status_code == 200
    body = response.content.decode()
    # Volver button points to the canonical list URL.
    assert 'href="/usuarios/"' in body
    assert "evil.example.com" not in body


@pytest.mark.django_db
def test_detail_oversized_return_falls_back_to_list(
    admin_client: Client, admin_user: User
) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    huge = "/usuarios/?role=ALUMNO&q=" + ("a" * 600)
    with _patch_mentor(returns=False):
        response = admin_client.get("/usuarios/ALU01/", {"return": huge})
    assert response.status_code == 200
    body = response.content.decode()
    assert 'href="/usuarios/"' in body
    assert "aaaaaa" not in body


@pytest.mark.django_db
def test_detail_unknown_matricula_returns_404(
    admin_client: Client, admin_user: User
) -> None:
    response = admin_client.get("/usuarios/NOPE/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Authorization gates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_anonymous_redirects_to_login() -> None:
    response = Client().get(LIST_URL)
    assert response.status_code in (302, 303)
    assert "/auth/" in response["Location"] or "login" in response["Location"].lower()


@pytest.mark.django_db
def test_list_alumno_gets_403(alumno_client: Client) -> None:
    assert alumno_client.get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_list_docente_gets_403(docente_client: Client) -> None:
    assert docente_client.get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_list_control_escolar_gets_403(ce_client: Client) -> None:
    assert ce_client.get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_list_responsable_programa_gets_403(rp_client: Client) -> None:
    assert rp_client.get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_detail_anonymous_redirects_to_login(admin_user: User) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    response = Client().get("/usuarios/ALU01/")
    assert response.status_code in (302, 303)


@pytest.mark.django_db
def test_detail_alumno_gets_403(alumno_client: Client) -> None:
    make_user(matricula="ALU01", role=Role.ALUMNO.value)
    assert alumno_client.get("/usuarios/ALU01/").status_code == 403
