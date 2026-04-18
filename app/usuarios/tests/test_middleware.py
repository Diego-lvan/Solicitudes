from __future__ import annotations

import logging
import time
from collections.abc import Callable

import jwt
import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.middleware import JwtAuthenticationMiddleware
from usuarios.models import User
from usuarios.services.user_service import DefaultUserService
from usuarios.tests.fakes import FakeRoleResolver, FakeSigaService, InMemoryUserRepository

JWT_SECRET = "test-secret-with-at-least-32-bytes-of-entropy!"
JWT_ALG = "HS256"


def _ok(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


def _build_middleware(
    get_response: Callable[[HttpRequest], HttpResponse] = _ok,
) -> JwtAuthenticationMiddleware:
    repo = InMemoryUserRepository()
    service = DefaultUserService(
        user_repository=repo,
        role_resolver=FakeRoleResolver(Role.ALUMNO),
        siga_service=FakeSigaService(unavailable=True),
        logger=logging.getLogger("test.mw"),
    )
    # The middleware's ORM lookup still hits the real DB; the in-memory repo
    # only owns the upsert side, so we also persist the User via Django ORM.
    return JwtAuthenticationMiddleware(get_response, user_service_factory=lambda: service)


def _mint(claims: dict[str, object]) -> str:
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)


@override_settings(JWT_SECRET=JWT_SECRET, JWT_ALGORITHM=JWT_ALG)
def test_anonymous_when_no_token() -> None:
    rf = RequestFactory()
    request = rf.get("/anything/")
    response = _build_middleware()(request)
    assert response.status_code == 200
    assert isinstance(request.user, AnonymousUser)


@pytest.mark.parametrize(
    "path",
    ["/health/", "/static/css/app.css", "/media/x.pdf", "/auth/callback?token=abc"],
)
@override_settings(JWT_SECRET=JWT_SECRET, JWT_ALGORITHM=JWT_ALG)
def test_skip_paths_bypass_jwt(path: str) -> None:
    rf = RequestFactory()
    request = rf.get(path, HTTP_AUTHORIZATION="Bearer not-a-real-token")
    response = _build_middleware()(request)
    assert response.status_code == 200
    assert isinstance(request.user, AnonymousUser)


@pytest.mark.django_db
@override_settings(JWT_SECRET=JWT_SECRET, JWT_ALGORITHM=JWT_ALG)
def test_valid_cookie_token_populates_request_user() -> None:
    # Persist the ORM user so middleware's User.objects.get() succeeds.
    User.objects.create(matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO.value)
    token = _mint(
        {
            "sub": "A1",
            "email": "a1@uaz.edu.mx",
            "rol": "alumno",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
    )
    rf = RequestFactory()
    request = rf.get("/protected/")
    request.COOKIES[SESSION_COOKIE_NAME] = token
    _build_middleware()(request)
    assert request.user.is_authenticated
    assert request.user.matricula == "A1"
    assert request.user_dto.matricula == "A1"  # type: ignore[attr-defined]


@pytest.mark.django_db
@override_settings(JWT_SECRET=JWT_SECRET, JWT_ALGORITHM=JWT_ALG)
def test_bearer_header_is_accepted_when_cookie_missing() -> None:
    User.objects.create(matricula="B1", email="b1@uaz.edu.mx", role=Role.ALUMNO.value)
    token = _mint(
        {
            "sub": "B1",
            "email": "b1@uaz.edu.mx",
            "rol": "alumno",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
    )
    rf = RequestFactory()
    request = rf.get("/protected/", HTTP_AUTHORIZATION=f"Bearer {token}")
    _build_middleware()(request)
    assert request.user.matricula == "B1"  # type: ignore[union-attr]


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    LOGIN_URL="https://idp.example.com/login",
)
def test_invalid_token_redirects_to_login() -> None:
    rf = RequestFactory()
    request = rf.get("/protected/")
    request.COOKIES[SESSION_COOKIE_NAME] = "not.a.jwt"
    response = _build_middleware()(request)
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"


@override_settings(
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    LOGIN_URL="https://idp.example.com/login",
)
def test_expired_token_redirects_to_login() -> None:
    token = _mint(
        {
            "sub": "A1",
            "email": "a1@uaz.edu.mx",
            "rol": "alumno",
            "exp": int(time.time()) - 60,
            "iat": int(time.time()) - 120,
        }
    )
    rf = RequestFactory()
    request = rf.get("/protected/")
    request.COOKIES[SESSION_COOKIE_NAME] = token
    response = _build_middleware()(request)
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/login"
