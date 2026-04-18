from __future__ import annotations

from django.test import Client, override_settings

from usuarios.constants import SESSION_COOKIE_NAME


@override_settings(AUTH_PROVIDER_LOGOUT_URL="https://idp.example.com/logout")
def test_logout_redirects_to_provider_and_clears_cookie() -> None:
    client = Client()
    client.cookies[SESSION_COOKIE_NAME] = "stale-token"
    response = client.get("/auth/logout")
    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.com/logout"
    assert response.cookies[SESSION_COOKIE_NAME].value == ""


@override_settings(AUTH_PROVIDER_LOGOUT_URL="")
def test_logout_falls_back_to_root_when_provider_url_empty() -> None:
    client = Client()
    response = client.get("/auth/logout")
    assert response.status_code == 302
    assert response["Location"] == "/"
