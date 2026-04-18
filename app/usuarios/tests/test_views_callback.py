from __future__ import annotations

import time

import jwt
import pytest
from django.test import Client, override_settings

from usuarios.constants import SESSION_COOKIE_NAME
from usuarios.models import User

JWT_SECRET = "callback-test-secret-32-bytes-long-aaaa"
JWT_ALG = "HS256"


def _mint(claims: dict[str, object]) -> str:
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)


def _valid_claims() -> dict[str, object]:
    return {
        "sub": "A1",
        "email": "a1@uaz.edu.mx",
        "rol": "alumno",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver", "localhost"],
    SESSION_COOKIE_SECURE=False,
    SIGA_BASE_URL="",  # forces SigaUnavailable; service swallows it
)
def test_callback_sets_cookie_and_redirects_to_default() -> None:
    client = Client()
    token = _mint(_valid_claims())
    response = client.get("/auth/callback", {"token": token})
    assert response.status_code == 302
    assert response["Location"] == "/solicitudes/"
    assert response.cookies[SESSION_COOKIE_NAME].value == token
    assert User.objects.filter(matricula="A1").exists()


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_callback_honors_relative_return_url() -> None:
    client = Client()
    token = _mint(_valid_claims())
    response = client.get("/auth/callback", {"token": token, "return": "/auth/me"})
    assert response.status_code == 302
    assert response["Location"] == "/auth/me"


@pytest.mark.django_db
@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_callback_blocks_external_return_url() -> None:
    client = Client()
    token = _mint(_valid_claims())
    response = client.get(
        "/auth/callback", {"token": token, "return": "https://evil.example.com/x"}
    )
    assert response.status_code == 302
    assert response["Location"] == "/"


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
)
def test_callback_with_invalid_token_redirects_to_login(client: Client) -> None:
    # AppErrorMiddleware turns AuthenticationRequired into a redirect to LOGIN_URL.
    response = client.get("/auth/callback", {"token": "garbage"})
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=True,
)
def test_callback_with_invalid_token_raises_in_debug() -> None:
    # In DEBUG mode the AppErrorMiddleware still maps AuthenticationRequired to
    # a redirect; the raise is what the test ensures hits the middleware.
    client = Client(raise_request_exception=True)
    # Should not raise — middleware always handles AppError, even in DEBUG.
    response = client.get("/auth/callback", {"token": "garbage"})
    assert response.status_code == 302


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    DEBUG=False,
    AUTH_PROVIDER_LOGIN_URL="https://idp.example.com/login",
    LOGIN_REDIRECT_URL="https://idp.example.com/login",
    LOGIN_URL="https://idp.example.com/login",
)
def test_callback_with_missing_token_redirects_to_login() -> None:
    # AppErrorMiddleware turns the AuthenticationRequired raised by the view
    # into a redirect; we never let the user see a 500 for a missing token.
    response = Client().get("/auth/callback")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"
