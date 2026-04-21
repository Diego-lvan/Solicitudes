"""Tests for the role-aware ``/`` landing view."""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings

from usuarios.constants import PROVIDER_ROLE_MAP, SESSION_COOKIE_NAME, Role

JWT_SECRET = "home-view-test-secret-32-bytes-long-aaaa"
JWT_ALG = "HS256"

# Reverse the provider-claim → Role map so the test can mint claims that the
# real `JwtRoleResolver` will accept (some role names differ from the enum's
# lowercased value, e.g. ``RESPONSABLE_PROGRAMA`` maps to ``resp_programa``).
_ROLE_TO_CLAIM = {role: claim for claim, role in PROVIDER_ROLE_MAP.items()}


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
        SIGA_BASE_URL="",
    ):
        yield


@pytest.mark.django_db
def test_home_redirects_admin_to_tipos_catalog() -> None:
    client = Client()
    client.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == "/solicitudes/admin/tipos/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "matricula", "expected_path"),
    [
        # Creators land on the intake catalog so they can file a solicitud.
        (Role.ALUMNO, "AL1", "/solicitudes/"),
        (Role.DOCENTE, "DC1", "/solicitudes/"),
        # Personal lands on the revision queue.
        (Role.CONTROL_ESCOLAR, "CE1", "/solicitudes/revision/"),
        (Role.RESPONSABLE_PROGRAMA, "RP1", "/solicitudes/revision/"),
    ],
)
def test_home_redirects_non_admin_roles_to_role_specific_landing(
    role: Role, matricula: str, expected_path: str
) -> None:
    client = Client()
    client.cookies[SESSION_COOKIE_NAME] = _mint(matricula, role)
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == expected_path


def test_home_redirects_anonymous_to_login() -> None:
    response = Client().get("/")
    assert response.status_code == 302
    assert "/auth/login" in response["Location"]
