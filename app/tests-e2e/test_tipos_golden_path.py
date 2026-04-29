"""Tier 2 browser E2E — tipos catalog golden path.

Plan acceptance: "admin creates a new TipoSolicitud with two FieldDefinitions;
lists it; edits it."

Auth uses the dev-login picker (DEBUG-only) since 003 layers atop the same
middleware chain 002 ships. Once 010 wires the real provider, only the entry
point changes; everything below it (cookie → middleware → admin view) stays
identical.
"""
from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-tipos-secret-with-32-bytes-or-more!"


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
def test_admin_creates_lists_and_edits_a_tipo(
    page: Page, live_server: Any
) -> None:
    # Reload usuarios.urls inside DEBUG=True so /auth/dev-login is mounted.
    from importlib import reload

    from django.urls import clear_url_caches

    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    base = live_server.url

    # ---- Log in as ADMIN through the dev picker ----
    page.goto(f"{base}/auth/dev-login")
    admin_row = (
        page.locator("li").filter(has_text="ADMIN").first
    )
    admin_row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")

    # ---- Create a new tipo with two fields ----
    page.goto(f"{base}/solicitudes/admin/tipos/nuevo/")
    expect(page.get_by_role("heading", name="Nuevo tipo de solicitud")).to_be_visible()

    page.get_by_label("Nombre", exact=False).first.fill("Constancia E2E")
    page.get_by_label("Descripción").fill("Tipo creado por la prueba E2E.")
    page.get_by_label("Rol responsable de revisión").select_option("CONTROL_ESCOLAR")
    page.get_by_label("Alumno").check()

    # Add and populate field rows ONE AT A TIME — clicking "Agregar campo"
    # collapses any previously-open row (by design, so the user focuses on
    # the new one), and a collapsed `.field-row-body` is `display: none`,
    # which makes its inputs un-fillable by Playwright. Fill each row before
    # adding the next.
    add_btn = page.get_by_role("button", name="Agregar campo")

    # First field: TEXT. ``order`` is rewritten by the JS on submit based
    # on DOM position, so the test no longer fills it.
    add_btn.click()
    page.locator('input[name="fields-0-label"]').fill("Nombre completo")
    page.locator('select[name="fields-0-field_type"]').select_option("TEXT")

    # Second field: SELECT with options entered through the chip UI.
    # The hidden ``options_csv`` input is filled by the chip JS, which mirrors
    # whatever the user typed (Enter-separated) into the visible chip input.
    add_btn.click()
    page.locator('input[name="fields-1-label"]').fill("Programa")
    page.locator('select[name="fields-1-field_type"]').select_option("SELECT")
    options_chip_cell = page.locator(
        '[data-options-for="id_fields-1-options_csv"]'
    )
    options_input = options_chip_cell.locator(".chip-input-text")
    options_input.fill("ISW")
    options_input.press("Enter")
    options_input.fill("ISC")
    options_input.press("Enter")

    page.get_by_role("button", name="Crear tipo").click()
    page.wait_for_load_state("networkidle")

    # Lands on detail page; assert the dynamic-form preview rendered.
    expect(page.get_by_role("heading", name="Constancia E2E")).to_be_visible()
    expect(page.get_by_text("Vista previa del formulario")).to_be_visible()
    expect(page.get_by_label("Nombre completo")).to_be_visible()
    expect(page.get_by_label("Programa")).to_be_visible()

    # ---- Lists it ----
    page.goto(f"{base}/solicitudes/admin/tipos/")
    expect(page.get_by_role("heading", name="Tipos de solicitud")).to_be_visible()
    expect(page.get_by_role("link", name="Constancia E2E")).to_be_visible()

    # ---- Edit it: rename and confirm change persists ----
    page.get_by_role("link", name="Constancia E2E").click()
    page.wait_for_load_state("networkidle")
    page.get_by_role("link", name="Editar").first.click()
    page.wait_for_load_state("networkidle")

    nombre_input = page.locator('input[name="nombre"]')
    nombre_input.fill("Constancia E2E (renombrada)")
    page.get_by_role("button", name="Guardar cambios").click()
    page.wait_for_load_state("networkidle")

    expect(
        page.get_by_role("heading", name="Constancia E2E (renombrada)")
    ).to_be_visible()


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
def test_admin_can_delete_middle_row_without_data_loss(
    page: Page, live_server: Any
) -> None:
    """Reviewer Critical: deleting a new mid-formset row must renumber survivors.

    Without renumbering, Django's formset reads ``fields-0`` and ``fields-1``
    only; the row originally posted as ``fields-2`` is silently dropped.
    """
    from importlib import reload

    from django.urls import clear_url_caches

    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    base = live_server.url
    page.goto(f"{base}/auth/dev-login")
    page.locator("li").filter(has_text="ADMIN").first.get_by_role(
        "button", name="Entrar"
    ).click()
    page.wait_for_load_state("networkidle")

    page.goto(f"{base}/solicitudes/admin/tipos/nuevo/")
    page.locator('input[name="nombre"]').fill("Renumber E2E")
    page.locator('select[name="responsible_role"]').select_option("CONTROL_ESCOLAR")
    page.get_by_label("Alumno").check()

    add = page.get_by_role("button", name="Agregar campo")
    add.click()
    page.locator('input[name="fields-0-label"]').fill("Primero")
    add.click()
    page.locator('input[name="fields-1-label"]').fill("Borrar")
    add.click()
    page.locator('input[name="fields-2-label"]').fill("Tercero")

    # Delete the middle (new) row. The JS must renumber the remaining rows
    # so that POST carries fields-0 (Primero) and fields-1 (Tercero).
    middle = page.locator(".field-row").nth(1)
    middle.locator(".field-row-delete-btn").click()

    # After renumber, "Tercero" is now row 1.
    expect(page.locator('input[name="fields-1-label"]')).to_have_value("Tercero")
    total = page.locator('input[name="fields-TOTAL_FORMS"]').input_value()
    assert total == "2", total

    page.get_by_role("button", name="Crear tipo").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_role("heading", name="Renumber E2E")).to_be_visible()
    expect(page.get_by_label("Primero")).to_be_visible()
    expect(page.get_by_label("Tercero")).to_be_visible()
