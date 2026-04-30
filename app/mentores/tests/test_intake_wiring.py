"""Tier 1 cross-feature E2E: mentores ↔ intake (Django Client, no browser).

Covers the §"E2E" + §"End-to-end smoke" + §"Cross-app wiring" sections of
the 008 plan. Exercises the real wiring (``MentoresIntakeAdapter`` → real
``MentorService`` → ORM repository), so the test stack is the same one that
runs in production.
"""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from mentores.constants import MentorSource
from mentores.models import MentorPeriodo
from mentores.tests.factories import make_admin_user
from solicitudes.lifecycle.constants import Estado
from solicitudes.models import Solicitud
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "mentores-intake-tier1-secret-32-bytes-aa"
JWT_ALG = "HS256"

_INTERNAL_TO_PROVIDER = {
    Role.ALUMNO: "alumno",
    Role.DOCENTE: "docente",
    Role.CONTROL_ESCOLAR: "control_escolar",
    Role.RESPONSABLE_PROGRAMA: "resp_programa",
    Role.ADMIN: "admin",
}


def _mint(matricula: str, role: Role) -> str:
    return jwt.encode(
        {
            "sub": matricula,
            "email": f"{matricula.lower()}@uaz.edu.mx",
            "rol": _INTERNAL_TO_PROVIDER[role],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


@pytest.fixture(autouse=True)
def _jwt_settings() -> Iterator[None]:
    with override_settings(
        JWT_SECRET=JWT_SECRET,
        JWT_ALGORITHM=JWT_ALG,
        ALLOWED_HOSTS=["testserver"],
        SIGA_BASE_URL="",
    ):
        yield


def _client(matricula: str, role: Role) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint(matricula, role)
    return c


def _make_paid_mentor_exempt_tipo() -> tuple[object, str]:
    """Tipo that requires payment AND is mentor-exempt; returns (tipo, field_attr)."""
    tipo = make_tipo(
        slug="constancia-mentor",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
        requires_payment=True,
        mentor_exempt=True,
    )
    field = make_field(
        tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value
    )
    return tipo, f"field_{str(field.id).replace('-', '')}"


def _seed_mentor(matricula: str) -> None:
    """Persist an active (open) ``MentorPeriodo`` for ``matricula``."""
    admin = make_admin_user()
    MentorPeriodo.objects.create(
        matricula=matricula,
        fuente=MentorSource.MANUAL.value,
        nota="",
        fecha_alta=timezone.now(),
        creado_por=admin,
    )


# ---- Tier 1 — cross-feature scenarios (plan §E2E) -----------------------


@pytest.mark.django_db
def test_mentor_intakes_exempt_tipo_without_comprobante() -> None:
    """Cross-feature: admin adds matricula M as mentor → alumno M intakes a
    ``mentor_exempt`` tipo → form does NOT require comprobante → resulting
    ``Solicitud.pago_exento == True``."""
    _seed_mentor("ALU1")
    _, field_attr = _make_paid_mentor_exempt_tipo()
    alumno = _client("ALU1", Role.ALUMNO)

    response = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia-mentor"}),
        data={field_attr: "Necesito constancia"},
    )
    assert response.status_code == 302
    s = Solicitud.objects.get()
    assert s.estado == Estado.CREADA.value
    assert s.pago_exento is True


@pytest.mark.django_db
def test_non_mentor_intake_requires_comprobante() -> None:
    """Cross-feature: alumno not in the mentor list submits the same
    ``mentor_exempt`` tipo → form requires comprobante; submitting without
    it returns 400 (form invalid)."""
    _, field_attr = _make_paid_mentor_exempt_tipo()
    alumno = _client("ALU2", Role.ALUMNO)

    response = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia-mentor"}),
        data={field_attr: "sin comprobante"},
    )
    # Bound form is rebuilt with comprobante required → form invalid → 400.
    assert response.status_code == 400
    assert Solicitud.objects.count() == 0
    form = response.context["form"]
    assert "comprobante" in form.errors


@pytest.mark.django_db
def test_non_mentor_intake_succeeds_when_comprobante_attached() -> None:
    """Same flow as above but with a comprobante attached → solicitud is
    created with ``pago_exento=False``."""
    _, field_attr = _make_paid_mentor_exempt_tipo()
    alumno = _client("ALU2", Role.ALUMNO)

    comprobante = SimpleUploadedFile(
        "comprobante.pdf",
        b"%PDF-1.4 fake pdf body",
        content_type="application/pdf",
    )
    response = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia-mentor"}),
        data={field_attr: "con comprobante", "comprobante": comprobante},
    )
    assert response.status_code == 302
    s = Solicitud.objects.get()
    assert s.pago_exento is False


@pytest.mark.django_db
def test_mentor_deactivation_preserves_existing_solicitud_snapshot() -> None:
    """Cross-feature snapshot integrity: admin deactivates mentor M; alumno M
    submits a NEW solicitud → comprobante now required. EXISTING solicitudes
    of M keep ``pago_exento=True`` (the boolean is stamped at creation, not
    re-evaluated on read).
    """
    _seed_mentor("ALU1")
    _, field_attr = _make_paid_mentor_exempt_tipo()
    alumno = _client("ALU1", Role.ALUMNO)

    # First create — while mentor is active.
    alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia-mentor"}),
        data={field_attr: "primera (con exención)"},
    )
    first = Solicitud.objects.get()
    assert first.pago_exento is True

    # Admin deactivates the mentor. We bypass the deactivate view here on
    # purpose: this test isolates the snapshot semantic ("pago_exento is
    # stamped at creation, never re-evaluated"), independent of how the row
    # gets flipped. The view-level path is covered by `test_views.py` and
    # `tests-e2e/test_mentores_golden_path.py`.
    MentorPeriodo.objects.filter(
        matricula="ALU1", fecha_baja__isnull=True
    ).update(fecha_baja=timezone.now())

    # Second create — now requires comprobante; without it, 400.
    response = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia-mentor"}),
        data={field_attr: "segunda (sin comprobante)"},
    )
    assert response.status_code == 400
    # No new row was created.
    assert Solicitud.objects.count() == 1

    # First solicitud still exempt — snapshot integrity.
    first.refresh_from_db()
    assert first.pago_exento is True


# ---- §"End-to-end smoke" -----------------------------------------------


@pytest.mark.django_db
def test_csv_import_100_rows_counts_add_up() -> None:
    """100-row CSV via the admin upload form: counts add up; invalid rows surface."""
    admin_user = make_admin_user(matricula="ADMIN_E2E")
    admin = _client("ADMIN_E2E", Role.ADMIN)

    rows = ["matricula"]
    for i in range(80):
        rows.append(f"{50000000 + i:08d}")  # unique inserts
    for i in range(15):
        rows.append("xxx")  # invalid format
    for i in range(5):
        rows.append(f"{50000000 + i:08d}")  # active duplicates of first 5

    payload = SimpleUploadedFile(
        "mentores.csv",
        ("\n".join(rows) + "\n").encode("utf-8"),
        content_type="text/csv",
    )

    response = admin.post(
        reverse("mentores:import_csv"), {"archivo": payload}
    )
    assert response.status_code == 200
    result = response.context["result"]
    assert result.total_rows == 100
    assert (
        result.inserted
        + result.skipped_duplicates
        + result.reactivated
        + len(result.invalid_rows)
        == 100
    )
    assert result.inserted == 80
    assert result.skipped_duplicates == 5
    assert len(result.invalid_rows) == 15
    # Verify creado_por is the actor — sanity-checks that intake's actor flows
    # through the form → service → repo layers.
    assert (
        MentorPeriodo.objects.filter(
            creado_por=admin_user, fecha_baja__isnull=True
        ).count()
        == 80
    )


@pytest.mark.django_db
def test_manual_add_duplicate_returns_409_with_friendly_message() -> None:
    """Manual add of an already-active matricula → 409 with a Spanish error."""
    _seed_mentor("33333333")
    # Pre-create the admin actor for consistency with the CSV-flow tests
    # that need a stable User row (see ``creado_por`` assertion in
    # ``test_csv_import_100_rows_counts_add_up``). The JWT middleware would
    # auto-provision this user otherwise, but explicit > implicit.
    make_admin_user(matricula="ADMIN_E2E")
    admin = _client("ADMIN_E2E", Role.ADMIN)
    response = admin.post(
        reverse("mentores:add"), {"matricula": "33333333"}
    )
    assert response.status_code == 409
    form = response.context["form"]
    errs = form.non_field_errors()
    assert any("mentor activo" in str(e) for e in errs)


@pytest.mark.django_db
def test_csv_import_reactivates_deactivated_matricula() -> None:
    """A deactivated matricula reappearing in a CSV import counts as reactivated."""
    _seed_mentor("44444444")
    MentorPeriodo.objects.filter(
        matricula="44444444", fecha_baja__isnull=True
    ).update(fecha_baja=timezone.now())

    _ = make_admin_user(matricula="ADMIN_E2E")
    admin = _client("ADMIN_E2E", Role.ADMIN)

    payload = SimpleUploadedFile(
        "mentores.csv",
        b"matricula\n44444444\n",
        content_type="text/csv",
    )
    response = admin.post(reverse("mentores:import_csv"), {"archivo": payload})
    assert response.status_code == 200
    result = response.context["result"]
    assert result.reactivated == 1
    assert result.inserted == 0
    # Reactivation opens a new period — there are now two rows for this
    # matrícula (one closed, one open). The new period is the active one.
    assert MentorPeriodo.objects.filter(matricula="44444444").count() == 2
    assert (
        MentorPeriodo.objects.filter(
            matricula="44444444", fecha_baja__isnull=True
        ).count()
        == 1
    )
