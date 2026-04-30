"""Tier 2 browser E2E — mentores admin golden paths.

Two flows per the 008 plan §E2E:
1. Admin imports a CSV of mentor matrículas via the upload form; success page
   shows the import counts; the catalog list shows the imported entries.
2. Admin deactivates a mentor from the list view (browser).

Captures screenshots at desktop (1280x900) and mobile (320x800) widths so the
UI can be visually verified per the frontend-design skill.
"""
from __future__ import annotations

from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-mentores-secret-with-32-bytes-or-more!!"

SCREENSHOT_DIR = Path("/tmp/screenshots-008")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    """Sign in via the dev-login picker as the seeded user with ``matricula``."""
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li.list-group-item").filter(has_text=matricula).first
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
def test_admin_imports_csv_and_sees_results_then_catalog(
    page: Page, live_server: Any, tmp_path: Path
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    _seed_admin()

    csv_path = tmp_path / "mentores.csv"
    csv_path.write_text("matricula\n90000001\n90000002\n90000003\n", encoding="utf-8")

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    # ---- Catálogo (empty) ----
    page.goto(f"{base}/mentores/")
    expect(page.get_by_role("heading", name="Catálogo de mentores")).to_be_visible()
    expect(page.get_by_text("Sin mentores registrados")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_list_empty_desktop.png"), full_page=True
    )

    # ---- Importar CSV ----
    page.get_by_role("link", name="Importar CSV").click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Importar mentores (CSV)")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_import_form_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_import_form_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    page.locator("input[type=file]").set_input_files(str(csv_path))
    page.get_by_role("button", name="Importar").click()
    page.wait_for_load_state("networkidle")

    # ---- Resultado ----
    expect(page.get_by_role("heading", name="Resultado de la importación")).to_be_visible()
    # Specific assertions on the count tiles so a regression that swapped
    # "Insertadas" with "Omitidas" would actually fail this test.
    dl = page.locator("dl").first
    expect(dl).to_contain_text("Total filas")
    expect(dl).to_contain_text("Insertadas")
    # The exact "3" should appear next to both Total filas and Insertadas;
    # checking the dl as a whole is enough since the labels constrain it.
    expect(dl.locator("dd")).to_contain_text(["3", "3", "0", "0"])
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_import_result_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_import_result_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- Catálogo (populated) ----
    page.get_by_role("link", name="Ir al catálogo").click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Catálogo de mentores")).to_be_visible()
    table = page.locator("table")
    expect(table).to_contain_text("90000001")
    expect(table).to_contain_text("90000002")
    expect(table).to_contain_text("90000003")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_list_populated_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_list_populated_mobile.png"),
        full_page=True,
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
def test_admin_deactivates_mentor_from_list_view(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    _seed_admin()

    # Seed an open mentor period so the row appears in the list.
    from django.utils import timezone

    from mentores.constants import MentorSource
    from mentores.models import MentorPeriodo
    from usuarios.models import User

    MentorPeriodo.objects.get_or_create(
        matricula="80000001",
        fecha_baja__isnull=True,
        defaults={
            "fuente": MentorSource.MANUAL.value,
            "nota": "",
            "fecha_alta": timezone.now(),
            "creado_por": User.objects.get(matricula="ADMIN_TEST"),
        },
    )

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    page.goto(f"{base}/mentores/")
    expect(page.locator("table")).to_contain_text("80000001")

    # Initiative 012 replaced the per-row "Desactivar" link with a bulk
    # action: tick the row's checkbox, hit the toolbar's "Desactivar"
    # button, confirm on the next page.
    page.locator('input[name="matriculas"][value="80000001"]').check()
    page.locator("#bulk-deactivate-form").get_by_role(
        "button", name="Desactivar"
    ).click()
    page.wait_for_load_state("networkidle")

    expect(
        page.get_by_role("heading", name="Confirmar desactivación")
    ).to_be_visible()
    expect(page.get_by_text("80000001")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_confirm_desktop.png"), full_page=True
    )

    page.get_by_role("button", name="Sí, desactivar seleccionados").click()
    page.wait_for_load_state("networkidle")

    # Back at the list with a success flash; the row no longer appears under
    # the default "Solo activos" filter.
    expect(page.locator(".alert-success")).to_contain_text("desactivado")
    # Positively assert the empty-state copy AND scope the row check to tbody
    # so future markup additions on this page don't silently weaken the test.
    expect(page.get_by_text("Sin mentores registrados")).to_be_visible()
    expect(
        page.locator("table tbody tr").filter(has_text="80000001")
    ).to_have_count(0)
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentores_list_after_deactivate_desktop.png"),
        full_page=True,
    )

    # Confirm row exists when filter is dropped.
    page.locator("input[name=only_active]").uncheck()
    page.get_by_role("button", name="Filtrar").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("table")).to_contain_text("80000001")
    expect(page.locator("table")).to_contain_text("Inactivo")
