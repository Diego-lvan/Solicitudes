from __future__ import annotations

import time

import jwt
import pytest
from django.test import Client, override_settings

from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.models import User

JWT_SECRET = "me-test-secret-32-bytes-long-aaaaaaaaa"
JWT_ALG = "HS256"


def _mint(sub: str, email: str) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "email": email,
            "rol": "alumno",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_me_renders_for_authenticated_user() -> None:
    User.objects.create(matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO.value)
    client = Client()
    client.cookies[SESSION_COOKIE_NAME] = _mint("A1", "a1@uaz.edu.mx")
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert b"A1" in response.content
    assert b"ALUMNO" in response.content


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
)
def test_me_redirects_anonymous_to_login() -> None:
    client = Client()
    response = client.get("/auth/me")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"
