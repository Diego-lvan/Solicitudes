"""Tier 1 in-process E2E: cross-feature auth integration via Django ``Client``.

Exercises the real middleware chain (request_id → logging → JWT auth →
error handler), the URL conf, and the ``/auth/me`` view — proving a JWT
holder can reach a protected page and that bad/expired tokens are bounced
to the provider login.
"""
from __future__ import annotations

import time

import jwt
import pytest
from django.test import Client, override_settings

from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.models import User

JWT_SECRET = "tier1-e2e-secret-32-bytes-of-entropy-aaa"
JWT_ALG = "HS256"


def _mint(claims: dict[str, object]) -> str:
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)


def _live_claims(sub: str = "E2E1", email: str = "e2e1@uaz.edu.mx") -> dict[str, object]:
    return {
        "sub": sub,
        "email": email,
        "rol": "alumno",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_full_callback_then_protected_view_with_cookie() -> None:
    """End-to-end: callback issues the cookie, the next request reaches /auth/me."""
    client = Client()
    token = _mint(_live_claims())
    callback = client.get("/auth/callback", {"token": token, "return": "/auth/me"})
    assert callback.status_code == 302
    assert callback["Location"] == "/auth/me"
    # Client persists the cookie set by the callback automatically.
    assert client.cookies[SESSION_COOKIE_NAME].value == token

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert b"E2E1" in me.content


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
    SIGA_BASE_URL="",
)
def test_expired_cookie_is_bounced_to_provider_login() -> None:
    User.objects.create(matricula="E2E2", email="e2e2@uaz.edu.mx", role=Role.ALUMNO.value)
    client = Client()
    expired = _mint(
        {
            "sub": "E2E2",
            "email": "e2e2@uaz.edu.mx",
            "rol": "alumno",
            "exp": int(time.time()) - 60,
            "iat": int(time.time()) - 120,
        }
    )
    client.cookies[SESSION_COOKIE_NAME] = expired
    response = client.get("/auth/me")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
)
def test_garbage_cookie_is_bounced_to_provider_login() -> None:
    client = Client()
    client.cookies[SESSION_COOKIE_NAME] = "definitely.not.a.jwt"
    response = client.get("/auth/me")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
)
def test_anonymous_request_to_protected_view_is_redirected() -> None:
    response = Client().get("/auth/me")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"
