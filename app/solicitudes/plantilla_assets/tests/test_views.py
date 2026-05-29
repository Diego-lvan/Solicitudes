"""View-layer tests for plantilla_assets admin views."""
from __future__ import annotations

import json
import time
from collections.abc import Iterator
from uuid import uuid4

import jwt
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.models import PlantillaAsset
from solicitudes.pdf.tests.factories import make_plantilla
from solicitudes.plantilla_assets.constants import MAX_ASSET_BYTES
from solicitudes.plantilla_assets.tests.factories import (
    PNG_1X1,
    make_global_asset,
    make_plantilla_asset,
)
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "plantilla-assets-test-secret-32-bytes-long-aa"
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


def _client_for(matricula: str, role: Role) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint(matricula, role)
    return c


@pytest.fixture
def admin_client() -> Client:
    return _client_for("ADMIN1", Role.ADMIN)


@pytest.fixture
def alumno_client() -> Client:
    return _client_for("A1", Role.ALUMNO)


# ---- auth ----


@pytest.mark.django_db
def test_anonymous_list_blocked() -> None:
    resp = Client().get(reverse("solicitudes:plantilla_assets:list"))
    assert resp.status_code in (302, 401)


@pytest.mark.django_db
def test_non_admin_list_forbidden(alumno_client: Client) -> None:
    resp = alumno_client.get(reverse("solicitudes:plantilla_assets:list"))
    assert resp.status_code == 403


# ---- list ----


@pytest.mark.django_db
def test_admin_list_renders(admin_client: Client) -> None:
    make_global_asset(nombre="Logo UAZ")
    resp = admin_client.get(reverse("solicitudes:plantilla_assets:list"))
    assert resp.status_code == 200
    assert "assets" in resp.context
    template_names = {t.name for t in resp.templates if t.name}
    assert "solicitudes/admin/plantilla_assets/list.html" in template_names


# ---- upload ----


@pytest.mark.django_db
def test_admin_upload_html_redirects(admin_client: Client) -> None:
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Logo UAZ", "imagen": upload},
    )
    assert resp.status_code == 302
    assert PlantillaAsset.objects.filter(slug="logo_uaz").exists()


@pytest.mark.django_db
def test_admin_upload_json_returns_201(admin_client: Client) -> None:
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Sello", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 201, resp.content
    payload = json.loads(resp.content)
    assert payload["slug"] == "sello"
    assert "snippet" in payload
    assert "thumb_url" in payload


@pytest.mark.django_db
def test_admin_upload_oversize_returns_422_json(admin_client: Client) -> None:
    big = b"\x00" * (MAX_ASSET_BYTES + 1)
    upload = SimpleUploadedFile("big.png", big, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Big", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 422, resp.content
    payload = json.loads(resp.content)
    assert "field_errors" in payload


# ---- list_json ----


@pytest.mark.django_db
def test_admin_list_json(admin_client: Client) -> None:
    plantilla = make_plantilla()
    g = make_global_asset(nombre="Glob A", slug="glob_a")
    pa = make_plantilla_asset(plantilla, nombre="P A", slug="p_a")

    resp = admin_client.get(
        reverse("solicitudes:plantilla_assets:list_json"),
        {"plantilla_id": str(plantilla.id)},
    )
    assert resp.status_code == 200
    payload = json.loads(resp.content)
    assert set(payload.keys()) == {"global", "plantilla"}
    glob_slugs = {row["slug"] for row in payload["global"]}
    plant_slugs = {row["slug"] for row in payload["plantilla"]}
    assert "glob_a" in glob_slugs
    assert "p_a" in plant_slugs
    assert g.slug in glob_slugs
    assert pa.slug in plant_slugs


# ---- delete ----


@pytest.mark.django_db
def test_admin_delete_get_renders_confirm(admin_client: Client) -> None:
    asset = make_global_asset()
    resp = admin_client.get(
        reverse("solicitudes:plantilla_assets:delete", kwargs={"asset_id": asset.id})
    )
    assert resp.status_code == 200
    assert "asset" in resp.context


@pytest.mark.django_db
def test_admin_delete_post_removes_asset(admin_client: Client) -> None:
    asset = make_global_asset()
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:delete", kwargs={"asset_id": asset.id})
    )
    assert resp.status_code == 302
    assert not PlantillaAsset.objects.filter(pk=asset.id).exists()


# ---- upload: HTML error branches ----


@pytest.mark.django_db
def test_admin_upload_html_form_errors_rerenders_400(admin_client: Client) -> None:
    big = b"\x00" * (MAX_ASSET_BYTES + 1)
    upload = SimpleUploadedFile("big.png", big, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Big", "imagen": upload},
    )
    assert resp.status_code == 400
    assert resp.context["form"].errors
    template_names = {t.name for t in resp.templates if t.name}
    assert "solicitudes/admin/plantilla_assets/list.html" in template_names


@pytest.mark.django_db
def test_admin_upload_html_domain_error_redirects(admin_client: Client) -> None:
    # A name that the form accepts (>=2 chars) but slugifies to empty,
    # so the service raises a DomainValidationError (InvalidImageType).
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "中文", "imagen": upload},
    )
    assert resp.status_code == 302
    assert not PlantillaAsset.objects.exists()


@pytest.mark.django_db
def test_admin_upload_json_domain_error_returns_422(admin_client: Client) -> None:
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "中文", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 422
    assert "field_errors" in json.loads(resp.content)


@pytest.mark.django_db(transaction=True)
def test_admin_upload_html_duplicate_slug_redirects(admin_client: Client) -> None:
    make_global_asset(nombre="Logo UAZ", slug="logo_uaz")
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Logo UAZ", "imagen": upload},
    )
    assert resp.status_code == 302
    assert PlantillaAsset.objects.filter(slug="logo_uaz").count() == 1


@pytest.mark.django_db
def test_admin_upload_json_duplicate_slug_returns_conflict(admin_client: Client) -> None:
    make_global_asset(nombre="Logo UAZ", slug="logo_uaz")
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse("solicitudes:plantilla_assets:upload_global"),
        data={"nombre": "Logo UAZ", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 409
    assert "error" in json.loads(resp.content)


# ---- per-plantilla upload ----


@pytest.mark.django_db
def test_admin_upload_for_plantilla_html_redirects_to_edit(admin_client: Client) -> None:
    plantilla = make_plantilla()
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Sello plantilla", "imagen": upload},
    )
    assert resp.status_code == 302
    assert "/plantillas/" in resp["Location"]
    assert PlantillaAsset.objects.filter(
        plantilla=plantilla, scope=PlantillaAsset.SCOPE_PLANTILLA
    ).exists()


@pytest.mark.django_db
def test_admin_upload_for_plantilla_json_returns_201(admin_client: Client) -> None:
    plantilla = make_plantilla()
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Sello json", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 201, resp.content
    payload = json.loads(resp.content)
    assert payload["scope"] == PlantillaAsset.SCOPE_PLANTILLA
    assert payload["plantilla_id"] == str(plantilla.id)


@pytest.mark.django_db
def test_admin_upload_for_plantilla_html_form_errors_redirect(admin_client: Client) -> None:
    plantilla = make_plantilla()
    big = b"\x00" * (MAX_ASSET_BYTES + 1)
    upload = SimpleUploadedFile("big.png", big, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Big", "imagen": upload},
    )
    assert resp.status_code == 302
    assert "/plantillas/" in resp["Location"]


@pytest.mark.django_db
def test_admin_upload_for_plantilla_json_form_errors_422(admin_client: Client) -> None:
    plantilla = make_plantilla()
    big = b"\x00" * (MAX_ASSET_BYTES + 1)
    upload = SimpleUploadedFile("big.png", big, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Big", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 422
    assert "field_errors" in json.loads(resp.content)


@pytest.mark.django_db
def test_admin_upload_for_plantilla_html_domain_error_redirect(admin_client: Client) -> None:
    plantilla = make_plantilla()
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "中文", "imagen": upload},
    )
    assert resp.status_code == 302
    assert not PlantillaAsset.objects.exists()


@pytest.mark.django_db
def test_admin_upload_for_plantilla_json_domain_error_422(admin_client: Client) -> None:
    plantilla = make_plantilla()
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "中文", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 422
    assert "field_errors" in json.loads(resp.content)


@pytest.mark.django_db
def test_admin_upload_for_plantilla_html_conflict_redirect(admin_client: Client) -> None:
    plantilla = make_plantilla()
    make_plantilla_asset(plantilla, nombre="Sello dup", slug="sello_dup")
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Sello dup", "imagen": upload},
    )
    assert resp.status_code == 302
    assert "/plantillas/" in resp["Location"]


@pytest.mark.django_db
def test_admin_upload_for_plantilla_json_conflict_409(admin_client: Client) -> None:
    plantilla = make_plantilla()
    make_plantilla_asset(plantilla, nombre="Sello dup", slug="sello_dup")
    upload = SimpleUploadedFile("sello.png", PNG_1X1, content_type="image/png")
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:upload_plantilla",
            kwargs={"plantilla_id": plantilla.id},
        ),
        data={"nombre": "Sello dup", "imagen": upload},
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 409
    assert "error" in json.loads(resp.content)


# ---- delete: error branches ----


@pytest.mark.django_db
def test_admin_delete_get_missing_redirects(admin_client: Client) -> None:
    resp = admin_client.get(
        reverse(
            "solicitudes:plantilla_assets:delete",
            kwargs={"asset_id": uuid4()},
        )
    )
    assert resp.status_code == 302


@pytest.mark.django_db
def test_admin_delete_post_missing_redirects(admin_client: Client) -> None:
    resp = admin_client.post(
        reverse(
            "solicitudes:plantilla_assets:delete",
            kwargs={"asset_id": uuid4()},
        )
    )
    assert resp.status_code == 302


# ---- list_json: malformed plantilla_id ----


@pytest.mark.django_db
def test_admin_list_json_bad_plantilla_id_ignored(admin_client: Client) -> None:
    make_global_asset(nombre="Glob B", slug="glob_b")
    resp = admin_client.get(
        reverse("solicitudes:plantilla_assets:list_json"),
        {"plantilla_id": "not-a-uuid"},
    )
    assert resp.status_code == 200
    payload = json.loads(resp.content)
    assert payload["plantilla"] == []
    assert {row["slug"] for row in payload["global"]} >= {"glob_b"}
