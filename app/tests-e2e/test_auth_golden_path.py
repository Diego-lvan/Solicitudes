"""Tier 2 browser E2E — auth golden path.

Plan acceptance: "Golden path: external login → land on profile → logout."

The "external login" entry point in initiative 002 is the DEBUG-only
``/auth/dev-login`` picker (initiative 010 swaps it for the real provider).
Everything *after* the entry point — JWT mint → ``/auth/callback`` → cookie →
``JwtAuthenticationMiddleware`` → protected view — is the production code path
that 010 will keep using as-is, so this test exercises the durable flow.
"""
from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-e2e-secret-with-32-bytes-or-more!!"


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(
    DEBUG=True,
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM="HS256",
    SIGA_BASE_URL="",  # SigaUnavailable is swallowed in hydrate_from_siga
    AUTH_PROVIDER_LOGOUT_URL="/auth/dev-login",  # bounces back to the picker in dev
    SESSION_COOKIE_SECURE=False,  # live_server is http, not https
)
def test_alumno_dev_login_lands_on_profile_and_logs_out(
    page: Page, live_server: Any
) -> None:
    # Re-reload urls.py *inside* the override_settings(DEBUG=True) scope to
    # guarantee the dev-login URL is mounted (the autouse fixture in
    # conftest.py runs before override_settings becomes active).
    from importlib import reload

    from django.urls import clear_url_caches

    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    base = live_server.url

    # 1. Land on the picker (DEBUG-only entry point)
    page.goto(f"{base}/auth/dev-login")
    expect(page.get_by_role("heading", name="Mi perfil")).not_to_be_visible()
    expect(page.locator("body")).to_contain_text("Login de desarrollo")

    # 2. Click "Entrar" on the ALUMNO quickstart row. The form has no visible
    #    text (just hidden inputs + submit button), so we filter on the
    #    surrounding <li> that holds the role label and the form together.
    alumno_row = page.locator("li.list-group-item").filter(has_text="ALUMNO").first
    alumno_row.get_by_role("button", name="Entrar").click()

    # 3. The picker → callback → cookie → /auth/me chain runs through the real
    #    middleware. We should now be on the profile page with the new user.
    expect(page).to_have_url(f"{base}/auth/me")
    expect(page.get_by_role("heading", name="Mi perfil")).to_be_visible()
    expect(page.locator("body")).to_contain_text("ALUMNO_TEST")
    expect(page.locator("body")).to_contain_text("alumno.test@uaz.edu.mx")
    expect(page.locator("body")).to_contain_text("ALUMNO")

    # 4. Session cookie is set.
    cookies_by_name = {c["name"]: c for c in page.context.cookies()}
    assert "stk" in cookies_by_name
    assert cookies_by_name["stk"]["value"]
    assert cookies_by_name["stk"]["httpOnly"] is True

    # 5. Click "Cerrar sesión" — should clear the cookie and bounce away.
    page.get_by_role("link", name="Cerrar sesión").click()

    # 6. Cookie is gone and we land back on the picker (dev's logout target).
    after_cookies = {c["name"]: c for c in page.context.cookies()}
    assert "stk" not in after_cookies or not after_cookies["stk"]["value"]
    expect(page).to_have_url(f"{base}/auth/dev-login")
    expect(page.locator("body")).to_contain_text("Login de desarrollo")
