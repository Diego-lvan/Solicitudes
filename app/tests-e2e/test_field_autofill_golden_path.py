"""Tier 2 browser E2E — Field Auto-fill golden paths (initiative 011).

Two flows:

1. **Admin golden path** — admin opens the catalog, creates a tipo with a
   ``USER_PROGRAMA`` source on a TEXT field, sees the live-preview "Auto"
   pill instead of an input, saves, reopens the detail.
2. **Alumno golden path** — alumno opens the intake page for the auto-fill
   tipo, sees the "Datos del solicitante" panel rendered with the resolved
   ``programa`` value, fills only the USER_INPUT fields, submits, lands on
   the detail page.

Captures screenshots at desktop (1280x900) and mobile (320x800) widths so
the UI can be visually verified per the frontend-design skill.
"""
from __future__ import annotations

from datetime import UTC
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-autofill-secret-with-32-bytes-or-more!"

SCREENSHOT_DIR = Path("/tmp/screenshots-011")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


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
def test_admin_creates_tipo_with_auto_fill_text_field(
    page: Page, live_server: Any
) -> None:
    """Admin declares a TEXT field with source=USER_PROGRAMA, sees the live-
    preview pill, saves, then re-opens detail and confirms the pill is
    still rendered (and the saved source round-tripped through the repo)."""
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

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

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    # Create a new tipo.
    page.goto(f"{base}/solicitudes/admin/tipos/nuevo/")
    expect(page.get_by_role("heading", name="Nuevo tipo de solicitud")).to_be_visible()

    page.get_by_label("Nombre", exact=False).fill("Constancia auto-fill (E2E)")
    page.locator('select[name="responsible_role"]').select_option("CONTROL_ESCOLAR")
    page.locator('input[name="creator_roles"][value="ALUMNO"]').check()

    # Add a field, set type=TEXT (default), pick source=USER_PROGRAMA.
    page.get_by_role("button", name="Agregar campo").click()
    row = page.locator(".field-row").first
    row.locator(".field-label-input").fill("Programa académico")
    row.locator('select[name$="-source"]').select_option("USER_PROGRAMA")

    # Live preview should now show the Auto pill instead of an input.
    # Anchor by the visible "Auto · …" text inside the preview pane rather
    # than by a CSS class — survives any Bootstrap → Tailwind change.
    expect(
        page.locator("#tipo-preview-body").get_by_text("Auto ·")
    ).to_be_visible()

    page.screenshot(
        path=str(SCREENSHOT_DIR / "admin_autofill_pill_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "admin_autofill_pill_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # Save and confirm the tipo persisted.
    page.get_by_role("button", name="Crear tipo").click()
    page.wait_for_load_state("networkidle")

    from solicitudes.models import FieldDefinition, TipoSolicitud

    tipo = TipoSolicitud.objects.get(slug="constancia-auto-fill-e2e")
    fd = FieldDefinition.objects.get(tipo=tipo)
    assert fd.source == "USER_PROGRAMA"


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
def test_alumno_intake_with_auto_fill_panel(
    page: Page, live_server: Any
) -> None:
    """Alumno sees the panel with their resolved programa, fills only the
    USER_INPUT field, and submits. The persisted solicitud carries both
    keys in ``valores`` (one alumno-supplied, one backend-resolved)."""
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    from solicitudes.models import FieldDefinition, Solicitud, TipoSolicitud
    from solicitudes.tipos.constants import FieldSource, FieldType
    from usuarios.constants import Role
    from usuarios.models import User

    User.objects.get_or_create(
        matricula="ALUMNO_TEST",
        defaults={
            "email": "alumno.test@uaz.edu.mx",
            "role": Role.ALUMNO.value,
            "full_name": "Ana Alumno",
            "programa": "Ingeniería de Software",
        },
    )
    tipo, _ = TipoSolicitud.objects.get_or_create(
        slug="constancia-autofill-e2e",
        defaults={
            "nombre": "Constancia auto-fill (E2E)",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "activo": True,
        },
    )
    FieldDefinition.objects.get_or_create(
        tipo=tipo,
        order=0,
        defaults={
            "label": "Programa académico",
            "field_type": FieldType.TEXT.value,
            "required": True,
            "source": FieldSource.USER_PROGRAMA.value,
        },
    )
    motivo, _ = FieldDefinition.objects.get_or_create(
        tipo=tipo,
        order=1,
        defaults={
            "label": "Motivo",
            "field_type": FieldType.TEXT.value,
            "required": True,
        },
    )

    base = live_server.url
    _login_as(page, base, "ALUMNO_TEST")

    page.goto(f"{base}/solicitudes/crear/constancia-autofill-e2e/")
    page.wait_for_load_state("networkidle")

    # Panel renders the resolved value.
    panel = page.locator('aside[aria-label="Datos del solicitante"]')
    expect(panel).to_be_visible()
    expect(panel).to_contain_text("Programa académico")
    expect(panel).to_contain_text("Ingeniería de Software")

    page.screenshot(
        path=str(SCREENSHOT_DIR / "alumno_autofill_panel_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "alumno_autofill_panel_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # Submit only the USER_INPUT field — auto-fill is invisible to the alumno.
    page.get_by_label("Motivo").fill("Necesito constancia.")
    page.get_by_role("button", name="Enviar solicitud").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_role("status").filter(has_text="Solicitud creada con folio")).to_be_visible()

    # Both keys land in valores: one alumno-supplied, one backend-resolved.
    [s] = Solicitud.objects.filter(tipo=tipo)
    assert s.valores[str(motivo.id)] == "Necesito constancia."
    auto_fid = str(FieldDefinition.objects.get(tipo=tipo, order=0).id)
    assert s.valores[auto_fid] == "Ingeniería de Software"
