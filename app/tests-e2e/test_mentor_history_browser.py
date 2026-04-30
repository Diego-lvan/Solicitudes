"""Tier 2 browser E2E — mentor history (initiative 012).

Two flows per the 012 plan §E2E:

1. Admin views a mentor's history at ``/mentores/<matricula>/`` — timeline
   shows both periods; status pill matches the latest period's open/closed
   state.
2. Admin reactivates a deactivated mentor via CSV import → opens the history
   page → sees the new (open) period at the top of the timeline; status pill
   is "Actualmente activo".

Captures screenshots at desktop (1280x900) and mobile (320x800) widths so
the UI can be visually verified per the frontend-design skill.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from importlib import reload
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from django.urls import clear_url_caches
from django.utils import timezone
from playwright.sync_api import Page, expect

JWT_SECRET = "tier2-mentor-history-secret-with-32-bytes-or-more!!"

SCREENSHOT_DIR = Path("/tmp/screenshots-012")


@pytest.fixture(autouse=True)
def _ensure_screenshot_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _login_as(page: Page, base: str, matricula: str) -> None:
    """Sign in via the dev-login picker as the seeded user with ``matricula``."""
    page.goto(f"{base}/auth/dev-login")
    row = page.locator("li.list-group-item").filter(has_text=matricula).first
    row.get_by_role("button", name="Entrar").click()
    page.wait_for_load_state("networkidle")


def _seed_admin() -> object:
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
    fecha_alta: datetime,
    fecha_baja: datetime | None,
    creado_por: Any,
) -> None:
    from mentores.constants import MentorSource
    from mentores.models import MentorPeriodo

    MentorPeriodo.objects.create(
        matricula=matricula,
        fuente=MentorSource.MANUAL.value,
        nota="",
        fecha_alta=fecha_alta,
        fecha_baja=fecha_baja,
        creado_por=creado_por,
    )


# ---------------------------------------------------------------------------
# Flow 1: view history (one closed + one open period)
# ---------------------------------------------------------------------------


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
def test_admin_views_mentor_history_with_two_periods(
    page: Page, live_server: Any
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    admin = _seed_admin()
    now = timezone.now()
    # Older closed period.
    _seed_period(
        "70000001",
        fecha_alta=now - timedelta(days=60),
        fecha_baja=now - timedelta(days=30),
        creado_por=admin,
    )
    # Newer open period.
    _seed_period(
        "70000001",
        fecha_alta=now - timedelta(days=10),
        fecha_baja=None,
        creado_por=admin,
    )

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    page.goto(f"{base}/mentores/70000001/")
    expect(
        page.get_by_role("heading", name=re.compile(r"Historial del mentor"))
    ).to_be_visible()
    expect(page.get_by_text("Actualmente activo")).to_be_visible()

    # Two timeline entries.
    items = page.locator("ol.list-group li.list-group-item")
    expect(items).to_have_count(2)

    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_history_two_periods_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_history_two_periods_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})


# ---------------------------------------------------------------------------
# Flow 2: reactivate via CSV → history reflects the new open period
# ---------------------------------------------------------------------------


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
def test_admin_reactivates_via_csv_and_history_shows_new_period(
    page: Page, live_server: Any, tmp_path: Path
) -> None:
    import usuarios.urls

    reload(usuarios.urls)
    clear_url_caches()

    admin = _seed_admin()
    now = timezone.now()
    # Single closed period — matrícula was a mentor and was deactivated.
    _seed_period(
        "70000002",
        fecha_alta=now - timedelta(days=20),
        fecha_baja=now - timedelta(days=5),
        creado_por=admin,
    )

    csv_path = tmp_path / "reactivar.csv"
    csv_path.write_text("matricula\n70000002\n", encoding="utf-8")

    base = live_server.url
    _login_as(page, base, "ADMIN_TEST")

    # CSV reactivation.
    page.goto(f"{base}/mentores/importar/")
    expect(
        page.get_by_role("heading", name="Importar mentores (CSV)")
    ).to_be_visible()
    page.set_input_files("input[type=file]", str(csv_path))
    page.get_by_role("button", name=re.compile(r"Importar|Subir")).click()
    page.wait_for_load_state("networkidle")

    # Result page shows the import counts. Find the "Reactivadas" card and
    # confirm its value is 1 — that's the contract guarantee.
    expect(page.get_by_text("Reactivadas")).to_be_visible()
    reactivadas_card = page.locator(".card", has_text="Reactivadas")
    expect(reactivadas_card.locator("dd")).to_have_text("1")

    # Now open the history page for that matrícula.
    page.goto(f"{base}/mentores/70000002/")
    expect(page.get_by_text("Actualmente activo")).to_be_visible()
    items = page.locator("ol.list-group li.list-group-item")
    expect(items).to_have_count(2)

    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_history_after_reactivation_desktop.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 320, "height": 800})
    page.screenshot(
        path=str(SCREENSHOT_DIR / "mentor_history_after_reactivation_mobile.png"),
        full_page=True,
    )
    page.set_viewport_size({"width": 1280, "height": 900})
