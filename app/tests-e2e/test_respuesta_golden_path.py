"""Tier 2 browser E2E — initiative 016 (Response Files & Comments).

Personal (CONTROL_ESCOLAR) opens a CREADA solicitud, atiende it, attaches
two response files with a comment, then finalizes. The alumno then logs in,
opens own detail, and sees the "Documentos de respuesta" section listing
both files for download.

Screenshots captured at 1280x900 (desktop) and 320x800 (mobile) for both
the revision and intake detail pages so the new cards can be visually
verified per the frontend-design skill.
"""
from __future__ import annotations

from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-respuesta-secret-with-32-bytes-or-more!"
SCREENSHOT_DIR = Path("/tmp/screenshots-016")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


def _logout(page: Page, base: str) -> None:
    # The dev-login page is the configured logout target.
    page.goto(f"{base}/auth/logout/")
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
def test_personal_uploads_respuesta_alumno_sees_it_after_finalizada(
    page: Page, live_server: Any, tmp_path: Path
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    from solicitudes.lifecycle.constants import Estado
    from solicitudes.lifecycle.tests.factories import make_solicitud
    from solicitudes.tipos.tests.factories import make_tipo
    from usuarios.constants import Role
    from usuarios.models import User

    # Personal + alumno fixtures the dev-login picker can locate.
    User.objects.get_or_create(
        matricula="ALU_RESP",
        defaults={
            "email": "alu.resp@uaz.edu.mx",
            "role": Role.ALUMNO.value,
            "full_name": "Ana Respuesta",
        },
    )
    User.objects.get_or_create(
        matricula="CE_RESP",
        defaults={
            "email": "ce.resp@uaz.edu.mx",
            "role": Role.CONTROL_ESCOLAR.value,
            "full_name": "Carlos Control",
        },
    )

    tipo = make_tipo(
        slug="constancia-respuesta",
        nombre="Constancia (Respuesta)",
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    alumno = User.objects.get(matricula="ALU_RESP")
    sol = make_solicitud(tipo=tipo, solicitante=alumno, estado=Estado.CREADA)

    # Two PDFs on disk for the multi-file upload.
    pdf_a = tmp_path / "constancia-firmada.pdf"
    pdf_b = tmp_path / "anexo.pdf"
    pdf_a.write_bytes(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    )
    pdf_b.write_bytes(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    )

    base = live_server.url

    # ---- 1. Personal opens revision detail, atiende, takes screenshots ----
    _login_as(page, base, "CE_RESP")
    page.goto(f"{base}/solicitudes/revision/{sol.folio}/")
    expect(page.get_by_role("heading", name=sol.folio)).to_be_visible()

    # Atender (CREADA → EN_PROCESO)
    page.get_by_role("button", name="Atender").click()
    page.wait_for_load_state("networkidle")

    # After atender, the "Adjuntar respuesta" card must be visible.
    expect(page.get_by_role("heading", name="Adjuntar respuesta")).to_be_visible()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_detail_en_proceso_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_detail_en_proceso_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 2. Upload two files + a comment ----
    page.get_by_label("Comentario (opcional)").fill(
        "Adjunto constancia firmada y un anexo."
    )
    page.locator("input[type=file][name=archivos]").set_input_files(
        [str(pdf_a), str(pdf_b)]
    )
    page.get_by_role("button", name="Adjuntar respuesta").click()
    page.wait_for_load_state("networkidle")

    # The "Respuestas entregadas" card now lists the batch with both files.
    expect(page.get_by_role("heading", name="Respuestas entregadas")).to_be_visible()
    entregadas = page.locator("article").filter(
        has_text="Respuestas entregadas"
    )
    expect(entregadas).to_contain_text("constancia-firmada.pdf")
    expect(entregadas).to_contain_text("anexo.pdf")
    expect(entregadas).to_contain_text("Adjunto constancia firmada y un anexo.")
    page.screenshot(
        path=str(SCREENSHOT_DIR / "revision_detail_entregadas_desktop.png"),
        full_page=True,
    )

    # ---- 3. Finalizar (EN_PROCESO → FINALIZADA) ----
    page.get_by_role("button", name="Finalizar").click()
    page.wait_for_load_state("networkidle")

    # ---- 4. Logout, login as alumno, verify "Documentos de respuesta" ----
    _logout(page, base)
    _login_as(page, base, "ALU_RESP")
    page.goto(f"{base}/solicitudes/{sol.folio}/")
    expect(page.get_by_role("heading", name=sol.folio)).to_be_visible()

    documentos = page.locator("article").filter(
        has_text="Documentos de respuesta"
    )
    expect(documentos).to_be_visible()
    expect(documentos).to_contain_text("constancia-firmada.pdf")
    expect(documentos).to_contain_text("anexo.pdf")
    expect(documentos).to_contain_text("Adjunto constancia firmada y un anexo.")

    # Alumno screenshots — desktop + mobile.
    page.screenshot(
        path=str(SCREENSHOT_DIR / "alumno_detail_documentos_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "alumno_detail_documentos_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 5. Download one of the response files ----
    with page.expect_download() as dl_info:
        documentos.get_by_role("link", name="Descargar").first.click()
    download = dl_info.value
    target = tmp_path / "downloaded.pdf"
    download.save_as(str(target))
    assert target.read_bytes().startswith(b"%PDF-")

    # Sanity: "Descargar PDF" affordance is GONE for the alumno (initiative 016).
    expect(
        page.get_by_role("link", name="Descargar PDF")
    ).to_have_count(0)
