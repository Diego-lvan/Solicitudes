"""Intake view tests — catalog, create, mis_solicitudes, detail, cancel."""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import Solicitud
from solicitudes.tipos.constants import FieldSource, FieldType
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role
from usuarios.tests.factories import make_user

JWT_SECRET = "intake-views-test-secret-32-bytes-long-aa"
JWT_ALG = "HS256"


def _mint(matricula: str, role: Role) -> str:
    return jwt.encode(
        {
            "sub": matricula,
            "email": f"{matricula.lower()}@uaz.edu.mx",
            "rol": role.value.lower(),
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


@pytest.fixture
def alumno_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ALU1", Role.ALUMNO)
    return c


@pytest.fixture
def docente_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("DOC1", Role.DOCENTE)
    return c


@pytest.fixture
def control_escolar_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("CE1", Role.CONTROL_ESCOLAR)
    return c


# ---- catalog ----


@pytest.mark.django_db
def test_catalog_lists_only_creator_role_active_tipos(
    alumno_client: Client,
) -> None:
    make_tipo(
        slug="alumno-tipo",
        nombre="Para alumnos",
        creator_roles=[Role.ALUMNO.value],
        activo=True,
    )
    make_tipo(
        slug="docente-tipo",
        nombre="Para docentes",
        creator_roles=[Role.DOCENTE.value],
        activo=True,
    )
    make_tipo(
        slug="alumno-inactivo",
        nombre="Inactivo",
        creator_roles=[Role.ALUMNO.value],
        activo=False,
    )
    response = alumno_client.get(reverse("solicitudes:intake:catalog"))
    assert response.status_code == 200
    slugs = {t.slug for t in response.context["tipos"]}
    assert slugs == {"alumno-tipo"}


@pytest.mark.django_db
def test_catalog_empty_for_personal_role(
    control_escolar_client: Client,
) -> None:
    response = control_escolar_client.get(reverse("solicitudes:intake:catalog"))
    assert response.status_code == 403  # CreatorRequiredMixin rejects personal.


# ---- create ----


@pytest.mark.django_db
def test_create_get_renders_form(alumno_client: Client) -> None:
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    make_field(tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value)
    response = alumno_client.get(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"})
    )
    assert response.status_code == 200
    assert "form" in response.context
    assert "tipo" in response.context


@pytest.mark.django_db
def test_create_post_persists_and_redirects_to_detail(
    alumno_client: Client,
) -> None:
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    field = make_field(tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value)
    field_attr = f"field_{str(field.id).replace('-', '')}"
    response = alumno_client.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={field_attr: "Necesito constancia"},
    )
    assert response.status_code == 302
    assert Solicitud.objects.count() == 1
    s = Solicitud.objects.first()
    assert s is not None
    assert s.estado == Estado.CREADA.value
    assert s.folio.startswith("SOL-")
    assert s.solicitante_id == "ALU1"
    assert s.historial.count() == 1


@pytest.mark.django_db
def test_create_post_invalid_form_renders_errors(
    alumno_client: Client,
) -> None:
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    make_field(
        tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value, required=True
    )
    response = alumno_client.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={},
    )
    assert response.status_code == 400
    assert Solicitud.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_creator_role_mismatch(
    alumno_client: Client,
) -> None:
    make_tipo(slug="docente-only", creator_roles=[Role.DOCENTE.value])
    response = alumno_client.get(
        reverse("solicitudes:intake:create", kwargs={"slug": "docente-only"})
    )
    # TipoService.get_for_creator raises Unauthorized → 403.
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_two_parallel_posts_yield_distinct_folios(
    alumno_client: Client,
) -> None:
    """Folio service is atomic — repeat creates produce monotonic folios."""
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    field = make_field(
        tipo, order=0, label="Motivo", field_type=FieldType.TEXT.value
    )
    field_attr = f"field_{str(field.id).replace('-', '')}"
    for i in range(2):
        alumno_client.post(
            reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
            data={field_attr: f"motivo {i}"},
        )
    folios = list(Solicitud.objects.values_list("folio", flat=True))
    assert len(folios) == 2
    assert len(set(folios)) == 2


# ---- auto-fill ----


@pytest.mark.django_db
def test_create_get_renders_solicitante_panel_with_resolved_values(
    alumno_client: Client,
) -> None:
    make_user(
        matricula="ALU1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO.value,
        full_name="Ana Alumno",
        programa="Ingeniería de Software",
    )
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    make_field(
        tipo,
        order=0,
        label="Programa",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_PROGRAMA.value,
        required=True,
    )
    make_field(
        tipo,
        order=1,
        label="Motivo",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_INPUT.value,
        required=True,
    )
    response = alumno_client.get(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"})
    )
    assert response.status_code == 200
    auto_fill = response.context["auto_fill"]
    assert auto_fill.has_missing_required is False
    assert ("Programa", "Ingeniería de Software") in auto_fill.items
    # Auto-fill field is NOT in the form; only the USER_INPUT one is.
    form = response.context["form"]
    assert len(form.fields) == 1


@pytest.mark.django_db
def test_create_get_flags_missing_required_when_programa_empty(
    alumno_client: Client,
) -> None:
    make_user(
        matricula="ALU1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO.value,
        full_name="Ana Alumno",
        programa="",  # missing — required auto-fill will flag
    )
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    make_field(
        tipo,
        order=0,
        label="Programa",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_PROGRAMA.value,
        required=True,
    )
    response = alumno_client.get(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"})
    )
    assert response.status_code == 200
    assert response.context["auto_fill"].has_missing_required is True
    # Submit button is rendered disabled.
    assert b"disabled" in response.content


@pytest.mark.django_db
def test_create_post_merges_auto_fill_values_into_persisted_valores(
    alumno_client: Client,
) -> None:
    make_user(
        matricula="ALU1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO.value,
        full_name="Ana Alumno",
        programa="Ingeniería de Software",
    )
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    auto_field = make_field(
        tipo,
        order=0,
        label="Programa",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_PROGRAMA.value,
        required=True,
    )
    motivo_field = make_field(
        tipo,
        order=1,
        label="Motivo",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_INPUT.value,
        required=True,
    )
    motivo_attr = f"field_{str(motivo_field.id).replace('-', '')}"
    response = alumno_client.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={motivo_attr: "Necesito constancia"},
    )
    assert response.status_code == 302
    [s] = Solicitud.objects.all()
    # Both keys present — auto-fill merged after form validation.
    assert s.valores == {
        str(motivo_field.id): "Necesito constancia",
        str(auto_field.id): "Ingeniería de Software",
    }


@pytest.mark.django_db
def test_create_post_drops_client_injection_for_auto_fill_field_id(
    alumno_client: Client,
) -> None:
    """Malicious client tries to set the auto-fill field's ``valores`` entry
    by POSTing ``field_<id>=...``. The form factory excluded the field, so
    the value never lands in ``form.to_values_dict()``; the resolver's
    backend value wins and the injected payload is dropped."""
    make_user(
        matricula="ALU1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO.value,
        full_name="Ana Alumno",
        programa="Ingeniería de Software",
    )
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    auto_field = make_field(
        tipo,
        order=0,
        label="Programa",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_PROGRAMA.value,
        required=True,
    )
    motivo_field = make_field(
        tipo,
        order=1,
        label="Motivo",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_INPUT.value,
        required=True,
    )
    motivo_attr = f"field_{str(motivo_field.id).replace('-', '')}"
    auto_attr = f"field_{str(auto_field.id).replace('-', '')}"
    response = alumno_client.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={motivo_attr: "ok", auto_attr: "INJECTED-PAYLOAD"},
    )
    assert response.status_code == 302
    [s] = Solicitud.objects.all()
    # Backend value wins; injection is dropped.
    assert s.valores[str(auto_field.id)] == "Ingeniería de Software"
    assert "INJECTED-PAYLOAD" not in str(s.valores.values())


@pytest.mark.django_db
def test_create_post_returns_422_when_required_auto_fill_missing(
    alumno_client: Client,
) -> None:
    make_user(
        matricula="ALU1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO.value,
        full_name="Ana Alumno",
        programa="",  # SIGA empty for required field
    )
    tipo = make_tipo(slug="constancia", creator_roles=[Role.ALUMNO.value])
    make_field(
        tipo,
        order=0,
        label="Programa",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_PROGRAMA.value,
        required=True,
    )
    motivo_field = make_field(
        tipo,
        order=1,
        label="Motivo",
        field_type=FieldType.TEXT.value,
        source=FieldSource.USER_INPUT.value,
        required=True,
    )
    motivo_attr = f"field_{str(motivo_field.id).replace('-', '')}"
    response = alumno_client.post(
        reverse("solicitudes:intake:create", kwargs={"slug": "constancia"}),
        data={motivo_attr: "ok"},
    )
    assert response.status_code == 422
    assert Solicitud.objects.count() == 0
    # The plan's acceptance criterion calls for a "clear error pointing
    # to Control Escolar". Pin the user-facing message so a regression
    # that swallowed ``AutoFillRequiredFieldMissing.user_message`` would
    # surface here, not just in production.
    assert b"Control Escolar" in response.content


# ---- mis_solicitudes ----


@pytest.mark.django_db
def test_mis_solicitudes_lists_only_owner(alumno_client: Client) -> None:
    owner = make_user(matricula="ALU1", email="alu1@uaz.edu.mx", role=Role.ALUMNO.value)
    other = make_user(matricula="OTHER", email="other@uaz.edu.mx", role=Role.ALUMNO.value)
    make_solicitud(solicitante=owner, folio="SOL-2026-00001")
    make_solicitud(solicitante=other, folio="SOL-2026-00002")
    response = alumno_client.get(reverse("solicitudes:intake:mis_solicitudes"))
    assert response.status_code == 200
    folios = {r.folio for r in response.context["page"].items}
    assert folios == {"SOL-2026-00001"}


# ---- detail ----


@pytest.mark.django_db
def test_detail_owner_can_view(alumno_client: Client) -> None:
    owner = make_user(matricula="ALU1", email="alu1@uaz.edu.mx", role=Role.ALUMNO.value)
    s = make_solicitud(solicitante=owner)
    response = alumno_client.get(
        reverse("solicitudes:intake:detail", kwargs={"folio": s.folio})
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_unrelated_alumno_rejected(alumno_client: Client) -> None:
    other = make_user(matricula="OTHER", email="other@uaz.edu.mx", role=Role.ALUMNO.value)
    s = make_solicitud(solicitante=other)
    response = alumno_client.get(
        reverse("solicitudes:intake:detail", kwargs={"folio": s.folio})
    )
    assert response.status_code == 403


# ---- cancel_own ----


@pytest.mark.django_db
def test_cancel_own_from_creada_succeeds(alumno_client: Client) -> None:
    owner = make_user(matricula="ALU1", email="alu1@uaz.edu.mx", role=Role.ALUMNO.value)
    s = make_solicitud(solicitante=owner, estado=Estado.CREADA)
    response = alumno_client.post(
        reverse("solicitudes:intake:cancel", kwargs={"folio": s.folio})
    )
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.CANCELADA.value


@pytest.mark.django_db
def test_cancel_own_from_en_proceso_blocked_with_friendly_redirect(
    alumno_client: Client,
) -> None:
    owner = make_user(matricula="ALU1", email="alu1@uaz.edu.mx", role=Role.ALUMNO.value)
    s = make_solicitud(solicitante=owner, estado=Estado.EN_PROCESO)
    response = alumno_client.post(
        reverse("solicitudes:intake:cancel", kwargs={"folio": s.folio})
    )
    # AppError is caught in the view and surfaces as a redirect with a flash.
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.estado == Estado.EN_PROCESO.value
