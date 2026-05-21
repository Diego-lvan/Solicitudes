"""View-layer tests for plantilla_assets admin views."""
from __future__ import annotations

import json
import time
from collections.abc import Iterator

import jwt
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from solicitudes.models import PlantillaAsset
from solicitudes.plantilla_assets.constants import MAX_ASSET_BYTES
from solicitudes.plantilla_assets.tests.factories import PNG_1X1, make_global_asset
from solicitudes.pdf.tests.factories import make_plantilla
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
    from solicitudes.plantilla_assets.tests.factories import make_plantilla_asset

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
