"""Tests for the DEBUG-only ``/auth/dev-login`` picker."""
from __future__ import annotations

from collections.abc import Iterator
from importlib import reload

import pytest
from django.test import Client, override_settings
from django.urls import clear_url_caches

import usuarios.urls
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.models import User

JWT_SECRET = "dev-login-test-secret-32-bytes-long-aaaa"
JWT_ALG = "HS256"


def _reload_urls() -> None:
    """Re-run ``usuarios.urls`` top-to-bottom against the *current*
    ``settings.DEBUG`` value, then drop Django's resolver caches."""
    reload(usuarios.urls)
    clear_url_caches()


@pytest.fixture(autouse=True)
def _reset_url_cache() -> Iterator[None]:
    """Each test starts with urlpatterns matching its overridden DEBUG, and
    finishes by restoring them to whatever the surrounding settings dictate
    (so suite-wide test order doesn't matter)."""
    _reload_urls()
    yield
    _reload_urls()


@pytest.mark.django_db
@override_settings(
    DEBUG=True,
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
    ROOT_URLCONF="config.urls",
)
def test_get_renders_picker_with_all_five_role_quickstarts() -> None:
    # Force urlconf re-import under DEBUG=True so /auth/dev-login is mounted.
    _reload_urls()

    response = Client().get("/auth/dev-login")
    assert response.status_code == 200
    body = response.content
    for role in Role:
        assert role.value.encode() in body


@pytest.mark.django_db
@override_settings(
    DEBUG=True,
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_quickstart_creates_user_and_round_trips_through_callback() -> None:
    _reload_urls()

    client = Client()
    # Quickstart fires an HTTP-302 to /auth/callback?token=...; client follows
    # that and lands at /auth/me with the cookie set.
    response = client.post(
        "/auth/dev-login",
        {"action": "quickstart", "role": Role.DOCENTE.value},
        follow=True,
    )
    assert response.status_code == 200
    assert b"DOCENTE_TEST" in response.content
    assert client.cookies[SESSION_COOKIE_NAME].value  # cookie was set
    assert User.objects.filter(matricula="DOCENTE_TEST", role=Role.DOCENTE.value).exists()


@pytest.mark.django_db
@override_settings(
    DEBUG=True,
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM=JWT_ALG,
    ALLOWED_HOSTS=["testserver"],
    SIGA_BASE_URL="",
)
def test_login_action_uses_existing_user() -> None:
    _reload_urls()

    User.objects.create(
        matricula="EXIST1", email="exist1@uaz.edu.mx", role=Role.ALUMNO.value
    )
    client = Client()
    response = client.post(
        "/auth/dev-login",
        {"action": "login", "matricula": "EXIST1"},
        follow=True,
    )
    assert response.status_code == 200
    assert b"EXIST1" in response.content


@pytest.mark.django_db
@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"])
def test_unknown_matricula_returns_400() -> None:
    _reload_urls()

    response = Client().post(
        "/auth/dev-login", {"action": "login", "matricula": "NOPE"}
    )
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"])
def test_unknown_action_returns_400() -> None:
    _reload_urls()

    response = Client().post("/auth/dev-login", {"action": "wat"})
    assert response.status_code == 400


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
def test_dev_login_url_is_not_registered_when_debug_false() -> None:
    """URL-level gate: the dev-login pattern must be absent from urlpatterns."""
    _reload_urls()

    pattern_names = {getattr(p, "name", None) for p in usuarios.urls.urlpatterns}
    assert "dev_login" not in pattern_names
    assert {"callback", "logout", "me"} <= pattern_names


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"])
def test_dev_login_url_is_registered_when_debug_true() -> None:
    _reload_urls()

    pattern_names = {getattr(p, "name", None) for p in usuarios.urls.urlpatterns}
    assert "dev_login" in pattern_names
