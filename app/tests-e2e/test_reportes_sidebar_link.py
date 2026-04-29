"""One-shot Tier 2 visual verification: admin sees the Reportes link in
the sidebar, and clicking it navigates to /reportes/.

Captures desktop (1280x900) and mobile (320x800) screenshots so the
sidebar wiring can be visually verified per the frontend-design skill.
"""
from __future__ import annotations

import re
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-reportes-sidebar-secret-32-bytes-or-more"

SCREENSHOT_DIR = Path("/tmp/screenshots-009-sidebar")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


def _seed_admin() -> None:
    from usuarios.constants import Role
    from usuarios.models import User

    User.objects.get_or_create(
        matricula="ADMIN_TEST",
        defaults={
            "email": "admin.test@uaz.edu.mx",
            "role": Role.ADMIN.value,
            "full_name": "Andrea Admin",
        },
    )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(
    DEBUG=True,
    JWT_SECRET=JWT_SECRET,
    JWT_ALGORITHM="HS256",
    SIGA_BASE_URL="",
    AUTH_PROVIDER_LOGOUT_URL="/auth/dev-login",
    SESSION_COOKIE_SECURE=False,
)
def test_admin_sidebar_has_reportes_link_and_it_navigates(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    _seed_admin()

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    # ---- Desktop: rail visible, link present, click navigates ----
    page.goto(f"{base}/")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "home_sidebar_desktop.png"), full_page=True
    )

    # The persistent sidebar is an <aside aria-label="Navegación lateral">
    # (the mobile drawer uses "Navegación móvil" so this disambiguates).
    sidebar = page.get_by_role("complementary", name="Navegación lateral")
    expect(sidebar.get_by_role("link", name="Dashboard")).to_be_visible()
    sidebar.get_by_role("link", name="Dashboard").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/reportes/$"))
    expect(page.get_by_role("heading", name="Reportes y dashboard")).to_be_visible()

    # ---- Mobile: open the drawer to verify the link appears there too ----
    page.goto(f"{base}/")
    page.set_viewport_size({"width": 320, "height": 800})
    page.get_by_role("button", name="Abrir menú").click()
    page.wait_for_timeout(400)  # drawer slide-in animation
    page.screenshot(
        path=str(SCREENSHOT_DIR / "home_sidebar_mobile.png"), full_page=True
    )
