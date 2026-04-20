"""View tests for the tipos admin feature.

Auth is driven through the real JWT middleware: tests mint a JWT (per the
project's existing pattern in ``usuarios.tests.test_e2e_tier1``), set it as
the ``stk`` cookie, and let the middleware materialize ``request.user``.
``client.force_login`` alone won't work because the JWT middleware overwrites
``request.user`` to ``AnonymousUser`` whenever the cookie is missing.
"""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.models import TipoSolicitud
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.tests.factories import make_field, make_tipo
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "tipos-views-test-secret-32-bytes-long-aa"
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
def admin_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    return c


@pytest.fixture
def alumno_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("A1", Role.ALUMNO)
    return c


# ---- list ----


@pytest.mark.django_db
def test_list_renders_for_admin(admin_client: Client) -> None:
    make_tipo(nombre="Constancia A", slug="constancia-a")
    make_tipo(nombre="Constancia B", slug="constancia-b")
    response = admin_client.get(reverse("solicitudes:tipos:list"))
    assert response.status_code == 200
    assert "tipos" in response.context
    assert {t.slug for t in response.context["tipos"]} == {"constancia-a", "constancia-b"}


@pytest.mark.django_db
def test_list_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.get(reverse("solicitudes:tipos:list"))
    # AdminRequiredMixin → Unauthorized → AppErrorMiddleware → 403.
    assert response.status_code == 403


@pytest.mark.django_db
def test_list_rejects_anonymous(client: Client) -> None:
    response = client.get(reverse("solicitudes:tipos:list"))
    # AuthenticationRequired → middleware redirect to provider login.
    assert response.status_code in (302, 401)


@pytest.mark.django_db
def test_list_filters_by_responsible_role(admin_client: Client) -> None:
    make_tipo(
        slug="ce", nombre="CE", responsible_role=Role.CONTROL_ESCOLAR.value
    )
    make_tipo(
        slug="rp", nombre="RP", responsible_role=Role.RESPONSABLE_PROGRAMA.value
    )
    response = admin_client.get(
        reverse("solicitudes:tipos:list"),
        {"responsible_role": Role.CONTROL_ESCOLAR.value},
    )
    assert response.status_code == 200
    assert {t.slug for t in response.context["tipos"]} == {"ce"}


@pytest.mark.django_db
def test_list_filters_by_only_active(admin_client: Client) -> None:
    make_tipo(slug="active", nombre="Active", activo=True)
    make_tipo(slug="inactive", nombre="Inactive", activo=False)
    response = admin_client.get(
        reverse("solicitudes:tipos:list"), {"only_active": "1"}
    )
    assert response.status_code == 200
    assert {t.slug for t in response.context["tipos"]} == {"active"}


# ---- create ----


@pytest.mark.django_db
def test_create_get_renders_empty_form(admin_client: Client) -> None:
    response = admin_client.get(reverse("solicitudes:tipos:create"))
    assert response.status_code == 200
    assert "tipo_form" in response.context
    assert "field_formset" in response.context


@pytest.mark.django_db
def test_create_post_persists_and_redirects(admin_client: Client) -> None:
    response = admin_client.post(
        reverse("solicitudes:tipos:create"),
        data={
            "nombre": "Constancia de Estudios",
            "descripcion": "",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "fields-TOTAL_FORMS": "1",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
            "fields-0-label": "Nombre",
            "fields-0-field_type": "TEXT",
            "fields-0-required": "on",
            "fields-0-order": "0",
        },
    )
    assert response.status_code == 302
    tipo = TipoSolicitud.objects.get(slug="constancia-de-estudios")
    assert tipo.fields.count() == 1
    assert response["Location"] == reverse(
        "solicitudes:tipos:detail", kwargs={"tipo_id": tipo.id}
    )


@pytest.mark.django_db
def test_create_post_invalid_renders_with_errors(admin_client: Client) -> None:
    response = admin_client.post(
        reverse("solicitudes:tipos:create"),
        data={
            "nombre": "ab",  # too short
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "fields-TOTAL_FORMS": "0",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
        },
    )
    assert response.status_code == 400
    assert response.context["tipo_form"].errors
    assert TipoSolicitud.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.post(
        reverse("solicitudes:tipos:create"),
        data={
            "nombre": "Hack",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "fields-TOTAL_FORMS": "0",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
        },
    )
    assert response.status_code == 403
    assert TipoSolicitud.objects.count() == 0


# ---- detail ----


@pytest.mark.django_db
def test_detail_renders_preview_form_when_fields_present(admin_client: Client) -> None:
    tipo = make_tipo()
    make_field(tipo, order=0, label="Nombre", field_type=FieldType.TEXT.value)
    response = admin_client.get(
        reverse("solicitudes:tipos:detail", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 200
    assert response.context["preview_form"] is not None


@pytest.mark.django_db
def test_detail_omits_preview_when_no_fields(admin_client: Client) -> None:
    tipo = make_tipo()
    response = admin_client.get(
        reverse("solicitudes:tipos:detail", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 200
    assert response.context["preview_form"] is None


# ---- edit ----


@pytest.mark.django_db
def test_edit_get_seeds_form_from_existing_tipo(admin_client: Client) -> None:
    tipo = make_tipo(nombre="Original")
    make_field(tipo, order=0, label="A", field_type=FieldType.TEXT.value)
    response = admin_client.get(
        reverse("solicitudes:tipos:edit", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 200
    assert response.context["tipo_form"].initial["nombre"] == "Original"
    assert len(response.context["field_formset"].initial) == 1


@pytest.mark.django_db
def test_edit_post_updates_fieldset(admin_client: Client) -> None:
    tipo = make_tipo()
    field = make_field(tipo, order=0, label="A", field_type=FieldType.TEXT.value)
    response = admin_client.post(
        reverse("solicitudes:tipos:edit", kwargs={"tipo_id": tipo.id}),
        data={
            "nombre": tipo.nombre,
            "responsible_role": tipo.responsible_role,
            "creator_roles": tipo.creator_roles,
            "fields-TOTAL_FORMS": "2",
            "fields-INITIAL_FORMS": "1",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
            "fields-0-field_id": str(field.id),
            "fields-0-label": "A renamed",
            "fields-0-field_type": "TEXT",
            "fields-0-required": "on",
            "fields-0-order": "0",
            "fields-1-label": "B",
            "fields-1-field_type": "NUMBER",
            "fields-1-required": "on",
            "fields-1-order": "1",
        },
    )
    assert response.status_code == 302
    tipo.refresh_from_db()
    labels = list(tipo.fields.order_by("order").values_list("label", flat=True))
    assert labels == ["A renamed", "B"]


# ---- deactivate ----


@pytest.mark.django_db
def test_deactivate_get_renders_confirmation(admin_client: Client) -> None:
    tipo = make_tipo()
    response = admin_client.get(
        reverse("solicitudes:tipos:deactivate", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 200
    assert response.context["tipo"].id == tipo.id


@pytest.mark.django_db
def test_deactivate_post_flips_flag(admin_client: Client) -> None:
    tipo = make_tipo(activo=True)
    response = admin_client.post(
        reverse("solicitudes:tipos:deactivate", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 302
    tipo.refresh_from_db()
    assert tipo.activo is False


@pytest.mark.django_db
def test_deactivate_rejects_non_admin(alumno_client: Client) -> None:
    tipo = make_tipo(activo=True)
    response = alumno_client.post(
        reverse("solicitudes:tipos:deactivate", kwargs={"tipo_id": tipo.id})
    )
    assert response.status_code == 403
    tipo.refresh_from_db()
    assert tipo.activo is True


@pytest.mark.django_db
def test_create_post_persists_three_fields_after_renumber(admin_client: Client) -> None:
    """Reviewer Critical: simulate the JS renumber-after-delete contract.

    The admin types 3 new field rows, deletes the middle one in the UI; the
    JS must renumber the survivors to a contiguous 0..1 sequence before submit.
    The server then sees TOTAL_FORMS=2 with prefixes ``fields-0`` and
    ``fields-1`` — both surviving labels — and persists both. This test
    represents the *post-renumber* POST shape and pins the contract so any
    future regression in the JS shows up here.
    """
    response = admin_client.post(
        reverse("solicitudes:tipos:create"),
        data={
            "nombre": "Tipo con renumber",
            "descripcion": "",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "fields-TOTAL_FORMS": "2",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
            "fields-0-label": "Primero",
            "fields-0-field_type": "TEXT",
            "fields-0-required": "on",
            "fields-0-order": "0",
            "fields-1-label": "Tercero",
            "fields-1-field_type": "TEXT",
            "fields-1-required": "on",
            "fields-1-order": "1",
        },
    )
    assert response.status_code == 302
    tipo = TipoSolicitud.objects.get(slug="tipo-con-renumber")
    labels = list(tipo.fields.order_by("order").values_list("label", flat=True))
    assert labels == ["Primero", "Tercero"], labels


@pytest.mark.django_db
def test_create_post_with_soft_deleted_row_compacts_orders(
    admin_client: Client,
) -> None:
    """Reviewer Important #1: soft-deleted rows must not consume order slots.

    When an admin marks a saved row as DELETE, ``rewriteOrderInputs`` skips
    it; the surviving rows post contiguous orders. ``_collect_fields`` then
    drops the DELETE row, and the persisted ``order`` values run 0..N-1.
    """
    response = admin_client.post(
        reverse("solicitudes:tipos:create"),
        data={
            "nombre": "Tipo compacta",
            "descripcion": "",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "fields-TOTAL_FORMS": "3",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "50",
            "fields-0-label": "Uno",
            "fields-0-field_type": "TEXT",
            "fields-0-required": "on",
            "fields-0-order": "0",
            "fields-1-label": "Borrar",
            "fields-1-field_type": "TEXT",
            "fields-1-required": "on",
            "fields-1-order": "0",  # JS skipped this row when rewriting
            "fields-1-DELETE": "on",
            "fields-2-label": "Dos",
            "fields-2-field_type": "TEXT",
            "fields-2-required": "on",
            "fields-2-order": "1",
        },
    )
    assert response.status_code == 302
    tipo = TipoSolicitud.objects.get(slug="tipo-compacta")
    rows = list(tipo.fields.order_by("order").values_list("label", "order"))
    assert rows == [("Uno", 0), ("Dos", 1)], rows
