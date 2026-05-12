"""Fixtures shared by archivos view/integration tests."""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings

from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "archivos-test-secret-32-bytes-long-aaaaaa"
JWT_ALG = "HS256"


def mint_token(matricula: str, role: Role) -> str:
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
def _jwt_settings(tmp_path: object) -> Iterator[None]:
    with override_settings(
        JWT_SECRET=JWT_SECRET,
        JWT_ALGORITHM=JWT_ALG,
        ALLOWED_HOSTS=["testserver"],
        SIGA_BASE_URL="",
        MEDIA_ROOT=tmp_path,
    ):
        yield


def make_client(matricula: str, role: Role) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = mint_token(matricula, role)
    return c
