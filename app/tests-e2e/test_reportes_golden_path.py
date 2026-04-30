"""Tier 2 browser E2E — reportes admin golden path.

Admin opens the dashboard, applies a filter, then exports CSV via the browser.
Captures screenshots at desktop (1280x900) and mobile (320x800) for visual
verification per the frontend-design skill.
"""
from __future__ import annotations

from datetime import UTC, datetime
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-reportes-secret-with-32-bytes-or-more!"

SCREENSHOT_DIR = Path("/tmp/screenshots-009")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li.list-group-item").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


def _seed_admin_and_data() -> None:
    from solicitudes.lifecycle.constants import Estado
    from solicitudes.lifecycle.tests.factories import make_solicitud
    from solicitudes.models import Solicitud
    from solicitudes.tipos.tests.factories import make_tipo
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
    tipo = make_tipo(slug="constancia-academica", nombre="Constancia académica")
    for _ in range(3):
        make_solicitud(tipo=tipo, estado=Estado.CREADA)
    finalized = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    Solicitud.objects.filter(pk=finalized.folio).update(
        created_at=datetime(2026, 4, 10, 12, tzinfo=UTC)
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
def test_admin_dashboard_filter_and_csv_export(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    _seed_admin_and_data()

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    # ---- Dashboard, no filter ----
    page.goto(f"{base}/reportes/")
    expect(page.get_by_role("heading", name="Reportes y dashboard")).to_be_visible()
    # Multiple matches (the filter dropdown option AND the per-tipo table row)
    # — assert presence on the first cell match.
    expect(
        page.get_by_role("cell", name="Constancia académica").first
    ).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "reportes_dashboard_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "reportes_dashboard_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- Apply estado filter ----
    page.locator("#filter_estado").select_option("CREADA")
    page.get_by_role("button", name="Aplicar").click()
    page.wait_for_load_state("networkidle")
    # Total tile shows 3 (only the CREADA-state solicitudes).
    expect(page.locator(".display-6").first).to_have_text("3")

    # ---- CSV export download ----
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Exportar CSV").click()
    download = download_info.value
    assert download.suggested_filename == "solicitudes.csv"
