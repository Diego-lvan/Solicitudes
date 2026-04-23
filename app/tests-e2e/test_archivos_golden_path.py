"""Tier 2 browser E2E — alumno attaches a real PDF, sees it on the detail
page, and downloads it.

Captures screenshots at desktop (1280x900) and mobile (320x800) so the
archivos UI rendered inside intake/detail.html can be visually verified per
the frontend-design skill.
"""
from __future__ import annotations

from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-archivos-secret-with-32-bytes-or-more!"
SCREENSHOT_DIR = Path("/tmp/screenshots-005")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
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
def test_alumno_attaches_pdf_sees_it_in_detail_and_downloads(
    page: Page, live_server: Any, tmp_path: Path
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    from solicitudes.models import FieldDefinition, TipoSolicitud
    from solicitudes.tipos.constants import FieldType
    from usuarios.constants import Role
    from usuarios.models import User

    User.objects.get_or_create(
        matricula="ALU_ARCH",
        defaults={
            "email": "alu.arch@uaz.edu.mx",
            "role": Role.ALUMNO.value,
            "full_name": "Ana Archivos",
        },
    )
    tipo, _ = TipoSolicitud.objects.get_or_create(
        slug="constancia-archivos",
        defaults={
            "nombre": "Constancia (Archivos)",
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
    _file_field, _ = FieldDefinition.objects.get_or_create(
        tipo=tipo,
        order=1,
        defaults={
            "label": "Documento de soporte",
            "field_type": FieldType.FILE.value,
            "required": True,
            "accepted_extensions": [".pdf"],
            "max_size_mb": 5,
        },
    )

    # Write a minimal valid-looking PDF on disk for the file input.
    pdf_path = tmp_path / "soporte.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    )

    base = live_server.url
    _login_as(page, base, "ALU_ARCH")

    page.goto(f"{base}/solicitudes/crear/constancia-archivos/")
    expect(page.get_by_role("heading", name="Constancia (Archivos)")).to_be_visible()

    page.get_by_label("Motivo").fill("Necesito la constancia.")
    page.get_by_label("Documento de soporte").set_input_files(str(pdf_path))

    page.get_by_role("button", name="Enviar solicitud").click()
    page.wait_for_load_state("networkidle")

    # Detail page lists the archivo and offers a download link.
    expect(page.locator(".alert-success")).to_contain_text("Solicitud creada")
    expect(page.get_by_role("heading", name="Archivos")).to_be_visible()
    expect(page.locator(".list-group-item")).to_contain_text("soporte.pdf")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_detail_archivos_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "intake_detail_archivos_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # Click "Descargar" → browser triggers a download.
    with page.expect_download() as dl_info:
        page.get_by_role("link", name="Descargar").first.click()
    download = dl_info.value
    target = tmp_path / "downloaded.pdf"
    download.save_as(str(target))
    assert target.read_bytes().startswith(b"%PDF-")
