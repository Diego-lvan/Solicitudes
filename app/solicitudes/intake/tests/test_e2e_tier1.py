"""Tier 1 cross-feature E2E for the solicitud lifecycle (Django Client, no browser)."""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.lifecycle.constants import Estado
from solicitudes.models import HistorialEstado, Solicitud
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "tier1-e2e-test-secret-32-bytes-long-aaa"
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


@pytest.mark.django_db
def test_alumno_creates_personal_atiende_and_finaliza() -> None:
    """Cross-feature happy path: intake → revision → finalizada."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    field = make_field(tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value)
    field_attr = f"field_{str(field.id).replace('-', '')}"

    alumno = _client("ALU1", Role.ALUMNO)
    ce = _client("CE1", Role.CONTROL_ESCOLAR)

    # Step 1 — alumno creates the solicitud.
    resp = alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "Necesito constancia"},
    )
    assert resp.status_code == 302
    s = Solicitud.objects.get()
    assert s.estado == Estado.CREADA.value
    assert s.folio.startswith("SOL-")
    assert HistorialEstado.objects.filter(solicitud=s).count() == 1

    # Step 2 — personal in responsible_role takes it.
    resp = ce.post(reverse("solicitudes:revision:take", kwargs={"folio": s.folio}))
    assert resp.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.EN_PROCESO.value
    assert HistorialEstado.objects.filter(solicitud=s).count() == 2

    # Step 3 — personal finalizes it.
    resp = ce.post(reverse("solicitudes:revision:finalize", kwargs={"folio": s.folio}))
    assert resp.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.FINALIZADA.value
    assert HistorialEstado.objects.filter(solicitud=s).count() == 3


@pytest.mark.django_db
def test_alumno_cancels_creada_then_blocked_on_en_proceso() -> None:
    """Owner cancellation: allowed in CREADA, blocked once EN_PROCESO."""
    tipo = make_tipo(
        slug="constancia",
        creator_roles=[Role.ALUMNO.value],
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    field = make_field(tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value)
    field_attr = f"field_{str(field.id).replace('-', '')}"

    alumno = _client("ALU1", Role.ALUMNO)
    ce = _client("CE1", Role.CONTROL_ESCOLAR)

    # Create and cancel from CREADA.
    alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "primer intento"},
    )
    s = Solicitud.objects.get()
    resp = alumno.post(
        reverse("solicitudes:intake:cancel", kwargs={"folio": s.folio})
    )
    assert resp.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.CANCELADA.value

    # Create another, take it (CE), then alumno tries to cancel from EN_PROCESO.
    alumno.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "segundo intento"},
    )
    s2 = Solicitud.objects.exclude(folio=s.folio).get()
    ce.post(reverse("solicitudes:revision:take", kwargs={"folio": s2.folio}))
    resp = alumno.post(
        reverse("solicitudes:intake:cancel", kwargs={"folio": s2.folio})
    )
    # AppError caught in the view → friendly redirect with flash; estado unchanged.
    assert resp.status_code == 302
    s2.refresh_from_db()
    assert s2.estado == Estado.EN_PROCESO.value


@pytest.mark.django_db
def test_two_creates_yield_distinct_folios() -> None:
    """Folio service is atomic — sequential creates produce distinct folios."""
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    field = make_field(tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value)
    field_attr = f"field_{str(field.id).replace('-', '')}"
    alumno_a = _client("ALU-A", Role.ALUMNO)
    alumno_b = _client("ALU-B", Role.ALUMNO)
    alumno_a.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "a"},
    )
    alumno_b.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "b"},
    )
    folios = list(Solicitud.objects.values_list("folio", flat=True))
    assert len(folios) == 2
    assert len(set(folios)) == 2


@pytest.mark.django_db
def test_snapshot_integrity_when_tipo_label_changes_after_creation() -> None:
    """A solicitud's snapshot is frozen — admin label edits do not retro-apply."""
    from solicitudes.models import FieldDefinition

    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    field = make_field(
        tipo, order=0, label="Motivo original", field_type=FieldType.TEXT.value
    )
    field_attr = f"field_{str(field.id).replace('-', '')}"

    _client("ALU1", Role.ALUMNO).post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "valor"},
    )
    s = Solicitud.objects.get()
    assert (
        s.form_snapshot["fields"][0]["label"] == "Motivo original"
    )

    # Admin edits the live label.
    fd = FieldDefinition.objects.get(pk=field.id)
    fd.label = "Motivo NUEVO"
    fd.save()

    # Re-read the solicitud detail; snapshot must still show the old label.
    s.refresh_from_db()
    assert s.form_snapshot["fields"][0]["label"] == "Motivo original"
