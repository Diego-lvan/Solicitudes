"""Tier 2 browser E2E — solicitud lifecycle golden paths.

Two flows:
1. Alumno creates a solicitud through the dynamic form (intake).
2. Personal in the responsible role takes a CREADA solicitud and finalizes it.

Captures screenshots at desktop (1280x900) and mobile (320x800) widths so the
UI can be visually verified per the frontend-design skill.
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

JWT_SECRET = "tier2-solicitud-secret-with-32-bytes-or-more!"

SCREENSHOT_DIR = Path("/tmp/screenshots-004")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    """Sign in via the dev-login picker as the seeded user with ``matricula``."""
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li.list-group-item").filter(has_text=matricula).first
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
def test_alumno_creates_solicitud_through_dynamic_form(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    # Seed users + a creator-role tipo with one TEXT field.
    from solicitudes.models import FieldDefinition, TipoSolicitud
    from solicitudes.tipos.constants import FieldType
    from usuarios.constants import Role
    from usuarios.models import User

    User.objects.get_or_create(
        matricula="ALUMNO_TEST",
        defaults={
            "email": "alumno.test@uaz.edu.mx",
            "role": Role.ALUMNO.value,
            "full_name": "Ana Alumno",
        },
    )
    tipo, _ = TipoSolicitud.objects.get_or_create(
        slug="constancia-e2e",
        defaults={
            "nombre": "Constancia (E2E)",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "activo": True,
        },
    )
    FieldDefinition.objects.get_or_create(
        tipo=tipo,
        order=0,
        defaults={
            "label": "Motivo",
            "field_type": FieldType.TEXT.value,
            "required": True,
        },
    )

    base = live_server.url
    _login_as(page, base, "ALUMNO_TEST")

    # ---- Catalog (desktop screenshot) ----
    page.goto(f"{base}/solicitudes/")
    expect(page.get_by_role("heading", name="Crear solicitud")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_catalog_desktop.png"), full_page=True
    )

    # Mobile reflow check.
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_catalog_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- Open the create form and submit ----
    page.get_by_role("link", name="Iniciar solicitud").first.click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Constancia (E2E)")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_create_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_create_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    page.get_by_label("Motivo").fill("Necesito una constancia.")
    page.get_by_role("button", name="Enviar solicitud").click()
    page.wait_for_load_state("networkidle")

    # Detail page renders the new folio + historial.
    expect(page.locator(".alert-success")).to_contain_text("Solicitud creada con folio")
    expect(page.get_by_role("heading", name="Datos de la solicitud")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_detail_desktop.png"), full_page=True
    )

    # Mis solicitudes lists the row.
    page.goto(f"{base}/solicitudes/mis/")
    expect(page.get_by_role("heading", name="Mis solicitudes")).to_be_visible()
    expect(page.locator("table")).to_contain_text("Constancia (E2E)")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_mis_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_mis_mobile.png"), full_page=True
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
def test_personal_takes_and_finalizes_solicitud(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    from datetime import datetime

    from solicitudes.formularios.schemas import FormSnapshot
    from solicitudes.lifecycle.constants import Estado
    from solicitudes.models import HistorialEstado, Solicitud, TipoSolicitud
    from usuarios.constants import Role
    from usuarios.models import User

    alumno, _ = User.objects.get_or_create(
        matricula="ALU-E2E",
        defaults={
            "email": "alu-e2e@uaz.edu.mx",
            "role": Role.ALUMNO.value,
            "full_name": "Alumna Demo",
        },
    )
    User.objects.get_or_create(
        matricula="CE_TEST",
        defaults={
            "email": "ce.test@uaz.edu.mx",
            "role": Role.CONTROL_ESCOLAR.value,
            "full_name": "Carla Control Escolar",
        },
    )
    tipo, _ = TipoSolicitud.objects.get_or_create(
        slug="constancia-revision-e2e",
        defaults={
            "nombre": "Constancia (Revisión E2E)",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "activo": True,
        },
    )
    snapshot = FormSnapshot(
        tipo_id=tipo.id,
        tipo_slug=tipo.slug,
        tipo_nombre=tipo.nombre,
        captured_at=datetime.now(tz=UTC),
        fields=[],
    ).model_dump(mode="json")
    s = Solicitud.objects.create(
        folio="SOL-2026-90001",
        tipo=tipo,
        solicitante=alumno,
        estado=Estado.CREADA.value,
        form_snapshot=snapshot,
        valores={},
        requiere_pago=False,
    )
    HistorialEstado.objects.create(
        solicitud=s,
        estado_nuevo=Estado.CREADA.value,
        actor=alumno,
        actor_role=Role.ALUMNO.value,
    )

    base = live_server.url
    _login_as(page, base, "CE_TEST")

    page.goto(f"{base}/solicitudes/revision/")
    expect(page.get_by_role("heading", name="Cola de revisión")).to_be_visible()
    expect(page.locator("table")).to_contain_text("SOL-2026-90001")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_queue_desktop.png"), full_page=True
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_queue_mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    page.get_by_role("link", name="Revisar").first.click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="SOL-2026-90001")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_detail_desktop.png"), full_page=True
    )

    # Take the solicitud (CREADA → EN_PROCESO).
    page.get_by_role("button", name="Atender").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".alert-success")).to_contain_text("tomada")

    s.refresh_from_db()
    assert s.estado == Estado.EN_PROCESO.value

    # Finalize it (EN_PROCESO → FINALIZADA).
    page.get_by_role("button", name="Finalizar").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".alert-success")).to_contain_text("finalizada")

    s.refresh_from_db()
    assert s.estado == Estado.FINALIZADA.value
