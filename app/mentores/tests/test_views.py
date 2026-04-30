"""View tests for the mentores admin feature.

Auth uses the real JWT middleware (same pattern as the tipos test suite):
mint a JWT, set the ``stk`` cookie, let middleware materialize ``request.user``.
"""
from __future__ import annotations

import time
from collections.abc import Iterator

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from mentores.constants import MentorSource
from mentores.models import Mentor
from mentores.tests.factories import make_admin_user, make_mentor
from usuarios.constants import SESSION_COOKIE_NAME, Role

JWT_SECRET = "mentores-views-test-secret-32-bytes-long-a"
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
def admin_user() -> object:
    return make_admin_user(matricula="ADMIN1", email="admin1@uaz.edu.mx")


@pytest.fixture
def admin_client(admin_user: object) -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("ADMIN1", Role.ADMIN)
    return c


@pytest.fixture
def alumno_client() -> Client:
    c = Client()
    c.cookies[SESSION_COOKIE_NAME] = _mint("A1", Role.ALUMNO)
    return c


# ---- list ----------------------------------------------------------------


@pytest.mark.django_db
def test_list_renders_for_admin(admin_client: Client, admin_user: object) -> None:
    make_mentor(matricula="11111111", creado_por=admin_user)
    make_mentor(matricula="22222222", creado_por=admin_user)
    response = admin_client.get(reverse("mentores:list"))
    assert response.status_code == 200
    rows = response.context["page"].items
    assert {m.matricula for m in rows} == {"11111111", "22222222"}


@pytest.mark.django_db
def test_list_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.get(reverse("mentores:list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_list_rejects_anonymous(client: Client) -> None:
    response = client.get(reverse("mentores:list"))
    # AuthenticationRequired → middleware redirects HTML clients to the
    # provider login (302); JSON clients would get 401. Default test
    # Client requests HTML, so we pin 302.
    assert response.status_code == 302


@pytest.mark.django_db
def test_list_only_active_filter_excludes_inactive(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor(matricula="11111111", activo=True, creado_por=admin_user)
    make_mentor(matricula="22222222", activo=False, creado_por=admin_user)
    response = admin_client.get(reverse("mentores:list") + "?only_active=1")
    assert response.status_code == 200
    rows = response.context["page"].items
    assert {m.matricula for m in rows} == {"11111111"}


# ---- add -----------------------------------------------------------------


@pytest.mark.django_db
def test_add_get_renders_form(admin_client: Client) -> None:
    response = admin_client.get(reverse("mentores:add"))
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_add_post_creates_mentor_and_redirects(admin_client: Client) -> None:
    response = admin_client.post(
        reverse("mentores:add"),
        {"matricula": "33333333", "nota": "Programa X"},
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))
    persisted = Mentor.objects.get(pk="33333333")
    assert persisted.activo is True
    assert persisted.fuente == MentorSource.MANUAL.value
    assert persisted.nota == "Programa X"


@pytest.mark.django_db
def test_add_post_with_invalid_matricula_rerenders_with_error(
    admin_client: Client,
) -> None:
    response = admin_client.post(reverse("mentores:add"), {"matricula": "abc"})
    assert response.status_code == 400
    form = response.context["form"]
    assert form.errors["matricula"]


@pytest.mark.django_db
def test_add_post_already_active_returns_conflict(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor(matricula="33333333", activo=True, creado_por=admin_user)
    response = admin_client.post(reverse("mentores:add"), {"matricula": "33333333"})
    assert response.status_code == 409
    form = response.context["form"]
    assert form.non_field_errors()


@pytest.mark.django_db
def test_add_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.post(reverse("mentores:add"), {"matricula": "33333333"})
    assert response.status_code == 403


# ---- deactivate ----------------------------------------------------------


@pytest.mark.django_db
def test_deactivate_get_renders_confirmation(admin_client: Client) -> None:
    response = admin_client.get(
        reverse("mentores:deactivate", kwargs={"matricula": "33333333"})
    )
    assert response.status_code == 200
    assert response.context["matricula"] == "33333333"


@pytest.mark.django_db
def test_deactivate_post_soft_deletes(admin_client: Client, admin_user: object) -> None:
    make_mentor(matricula="33333333", activo=True, creado_por=admin_user)
    response = admin_client.post(
        reverse("mentores:deactivate", kwargs={"matricula": "33333333"})
    )
    assert response.status_code == 302
    assert Mentor.objects.get(pk="33333333").activo is False


@pytest.mark.django_db
def test_deactivate_missing_matricula_redirects_with_error(
    admin_client: Client,
) -> None:
    response = admin_client.post(
        reverse("mentores:deactivate", kwargs={"matricula": "99999999"})
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))


# ---- import_csv ----------------------------------------------------------


@pytest.mark.django_db
def test_import_csv_get_renders_form(admin_client: Client) -> None:
    response = admin_client.get(reverse("mentores:import_csv"))
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_import_csv_post_returns_result_page(admin_client: Client) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    payload = SimpleUploadedFile(
        "mentores.csv",
        b"matricula\n44444444\n55555555\nbad\n",
        content_type="text/csv",
    )
    response = admin_client.post(
        reverse("mentores:import_csv"), {"archivo": payload}
    )
    assert response.status_code == 200
    result = response.context["result"]
    assert result.total_rows == 3
    assert result.inserted == 2
    assert len(result.invalid_rows) == 1


@pytest.mark.django_db
def test_import_csv_post_with_bad_header_rerenders_with_error(
    admin_client: Client,
) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    payload = SimpleUploadedFile(
        "bad.csv",
        b"alumno\n44444444\n",
        content_type="text/csv",
    )
    response = admin_client.post(
        reverse("mentores:import_csv"), {"archivo": payload}
    )
    assert response.status_code == 422  # DomainValidationError → 422
    form = response.context["form"]
    assert form.errors["archivo"]


@pytest.mark.django_db
def test_import_csv_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.get(reverse("mentores:import_csv"))
    assert response.status_code == 403
