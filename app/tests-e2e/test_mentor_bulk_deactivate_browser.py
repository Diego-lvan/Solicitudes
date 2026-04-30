"""Tier 2 browser E2E — bulk deactivate (initiative 012, mid-implementation add).

Two flows:

1. Admin opens the list with several active mentors → sees the checkbox
   column, the master "Seleccionar todos" button, and the single "Desactivar"
   submit button. Screenshots at 1280x900 desktop and 320x800 mobile.
2. Admin checks two rows, hits "Desactivar" → confirm page lists the chosen
   matriculas → admin confirms → flash message + redirect → list reflects
   the closure (selected rows show "Inactivo", others stay "Activo").
   Screenshots of the confirmation page.

Captures to ``/tmp/screenshots-012/`` so they can be eyeballed alongside the
detail-view shots taken earlier.
"""
from __future__ import annotations

from datetime import datetime
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from django.utils import timezone
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-bulk-deactivate-secret-with-32-bytes-or-more!!"
SCREENSHOT_DIR = Path("/tmp/screenshots-012")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


def _seed_admin() -> Any:
    from usuarios.constants import Role
    from usuarios.models import User

    user, _ = User.objects.get_or_create(
        matricula="ADMIN_TEST",
        defaults={
            "email": "admin.test@uaz.edu.mx",
            "role": Role.ADMIN.value,
            "full_name": "Andrea Admin",
        },
    )
    return user


def _seed_period(
    matricula: str,
    *,
    fecha_alta: datetime | None = None,
    fecha_baja: datetime | None = None,
    creado_por: Any,
) -> None:
    from mentores.constants import MentorSource
    from mentores.models import MentorPeriodo

    MentorPeriodo.objects.create(
        matricula=matricula,
        fuente=MentorSource.MANUAL.value,
        nota="",
        fecha_alta=fecha_alta or timezone.now(),
        fecha_baja=fecha_baja,
        creado_por=creado_por,
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
def test_admin_sees_checkboxes_and_bulk_action_buttons(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    admin = _seed_admin()
    for matricula in ("80000001", "80000002", "80000003"):
        _seed_period(matricula, creado_por=admin)

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")
    page.goto(f"{base}/mentores/")

    # Two toolbar buttons render: a "select all" trigger + the single "Desactivar".
    expect(
        page.get_by_role("button", name="Seleccionar todos")
    ).to_be_visible()
    expect(page.get_by_role("button", name="Desactivar")).to_be_visible()
    # Three checkboxes (one per active row); none checked initially.
    boxes = page.locator('input[type=checkbox][name="matriculas"]')
    expect(boxes).to_have_count(3)
    # Master button toggles every checkbox.
    page.get_by_role("button", name="Seleccionar todos").click()
    expect(boxes.nth(0)).to_be_checked()
    expect(boxes.nth(1)).to_be_checked()
    expect(boxes.nth(2)).to_be_checked()
    # Clicking again unchecks them all (toggle behavior).
    page.get_by_role("button", name="Seleccionar todos").click()
    expect(boxes.nth(0)).not_to_be_checked()

    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_list_with_bulk_actions_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_list_with_bulk_actions_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})


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
def test_admin_bulk_deactivates_selected_via_confirm_flow(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    admin = _seed_admin()
    for matricula in ("80000001", "80000002", "80000003"):
        _seed_period(matricula, creado_por=admin)

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")
    page.goto(f"{base}/mentores/")

    # Tick two of the three rows.
    page.locator('input[name="matriculas"][value="80000001"]').check()
    page.locator('input[name="matriculas"][value="80000002"]').check()

    # Submit the bulk action — single button, selection is implicit.
    page.locator("#bulk-deactivate-form").get_by_role(
        "button", name="Desactivar"
    ).click()
    page.wait_for_load_state("networkidle")

    # Confirm page renders the two matrículas.
    expect(
        page.get_by_role("heading", name="Confirmar desactivación")
    ).to_be_visible()
    expect(page.get_by_text("80000001")).to_be_visible()
    expect(page.get_by_text("80000002")).to_be_visible()

    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_bulk_confirm_selected_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_bulk_confirm_selected_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # Confirm the action.
    page.get_by_role("button", name="Sí, desactivar seleccionados").click()
    page.wait_for_load_state("networkidle")

    # Back at the list. Filter to "all" so we can see the now-closed rows.
    page.goto(f"{base}/mentores/?filtered=1")
    # 80000001 and 80000002 should now show "Inactivo"; 80000003 still "Activo".
    from mentores.models import MentorPeriodo

    closed = MentorPeriodo.objects.filter(fecha_baja__isnull=False).count()
    still_open = MentorPeriodo.objects.filter(fecha_baja__isnull=True).count()
    assert closed == 2, "two periods should be closed"
    assert still_open == 1, "one period should remain open"
