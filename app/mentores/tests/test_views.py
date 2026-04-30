"""View tests for the mentores admin feature.

Auth uses the real JWT middleware (same pattern as the tipos test suite):
mint a JWT, set the ``stk`` cookie, let middleware materialize ``request.user``.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import timedelta

import jwt
import pytest
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from mentores.constants import MentorSource
from mentores.models import MentorPeriodo
from mentores.tests.factories import make_admin_user, make_mentor_periodo
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
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    make_mentor_periodo(matricula="22222222", creado_por=admin_user)
    response = admin_client.get(reverse("mentores:list"))
    assert response.status_code == 200
    rows = response.context["page"].items
    assert {m.matricula for m in rows} == {"11111111", "22222222"}


@pytest.mark.django_db
def test_list_links_each_matricula_to_detail_view(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    response = admin_client.get(reverse("mentores:list"))
    assert response.status_code == 200
    detail_url = reverse("mentores:detail", kwargs={"matricula": "11111111"})
    assert detail_url.encode() in response.content


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
def test_list_only_active_filter_excludes_closed_periods(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    make_mentor_periodo(
        matricula="22222222", creado_por=admin_user, fecha_baja=timezone.now()
    )
    response = admin_client.get(
        reverse("mentores:list") + "?filtered=1&only_active=1"
    )
    assert response.status_code == 200
    rows = response.context["page"].items
    assert {m.matricula for m in rows} == {"11111111"}


# ---- detail (NEW in 012) -------------------------------------------------


@pytest.mark.django_db
def test_detail_renders_history_newest_first(
    admin_client: Client, admin_user: object
) -> None:
    now = timezone.now()
    make_mentor_periodo(
        matricula="11111111",
        creado_por=admin_user,
        fecha_alta=now - timedelta(days=30),
        fecha_baja=now - timedelta(days=20),
    )
    make_mentor_periodo(
        matricula="11111111",
        creado_por=admin_user,
        fecha_alta=now - timedelta(hours=1),
    )
    response = admin_client.get(
        reverse("mentores:detail", kwargs={"matricula": "11111111"})
    )
    assert response.status_code == 200
    history = response.context["history"]
    assert len(history) == 2
    # Newest first.
    assert history[0].fecha_alta > history[1].fecha_alta
    assert response.context["is_currently_active"] is True


@pytest.mark.django_db
def test_detail_status_inactive_when_no_open_period(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor_periodo(
        matricula="11111111",
        creado_por=admin_user,
        fecha_baja=timezone.now(),
    )
    response = admin_client.get(
        reverse("mentores:detail", kwargs={"matricula": "11111111"})
    )
    assert response.status_code == 200
    assert response.context["is_currently_active"] is False


@pytest.mark.django_db
def test_detail_returns_404_for_unknown_matricula(admin_client: Client) -> None:
    response = admin_client.get(
        reverse("mentores:detail", kwargs={"matricula": "99999999"})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.get(
        reverse("mentores:detail", kwargs={"matricula": "99999999"})
    )
    assert response.status_code == 403


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
    persisted = MentorPeriodo.objects.get(
        matricula="33333333", fecha_baja__isnull=True
    )
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
    make_mentor_periodo(matricula="33333333", creado_por=admin_user)
    response = admin_client.post(
        reverse("mentores:add"), {"matricula": "33333333"}
    )
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
def test_deactivate_post_closes_open_period_and_records_actor(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor_periodo(matricula="33333333", creado_por=admin_user)
    response = admin_client.post(
        reverse("mentores:deactivate", kwargs={"matricula": "33333333"})
    )
    assert response.status_code == 302
    persisted = MentorPeriodo.objects.get(matricula="33333333")
    assert persisted.fecha_baja is not None
    assert persisted.desactivado_por_id == "ADMIN1"


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


# ---- bulk deactivate -----------------------------------------------------


_BULK_SALT = "mentores.bulk_deactivate"


def _bulk_token(action: str, matriculas: list[str]) -> str:
    """Mint a valid signed token directly (mirrors what step 1 emits)."""
    from django.core import signing

    return signing.dumps(
        {"action": action, "matriculas": sorted(set(matriculas))},
        salt=_BULK_SALT,
    )


@pytest.mark.django_db
def test_bulk_deactivate_step1_renders_confirm_with_token(
    admin_client: Client, admin_user: object
) -> None:
    """Step 1 — no token → render confirmation page with a fresh signed token; no DB writes."""
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    make_mentor_periodo(matricula="22222222", creado_por=admin_user)
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"),
        {"action": "selected", "matriculas": ["11111111", "22222222"]},
    )
    assert response.status_code == 200
    assert response.context["action"] == "selected"
    # The view dedupes + sorts before signing, so the rendered list is deterministic.
    assert list(response.context["matriculas"]) == ["11111111", "22222222"]
    assert response.context["token"]  # token is non-empty
    # Nothing closed yet.
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=True).count() == 2


@pytest.mark.django_db
def test_bulk_deactivate_step2_applies_with_valid_token(
    admin_client: Client, admin_user: object
) -> None:
    """Step 2 — valid token → close matriculas in the token + flash + redirect."""
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    make_mentor_periodo(matricula="22222222", creado_por=admin_user)
    make_mentor_periodo(matricula="33333333", creado_por=admin_user)  # not in token

    token = _bulk_token("selected", ["11111111", "22222222"])
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"), {"token": token}
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))
    assert MentorPeriodo.objects.filter(
        matricula="33333333", fecha_baja__isnull=True
    ).count() == 1
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=False).count() == 2
    closed = MentorPeriodo.objects.get(matricula="11111111")
    assert closed.desactivado_por_id == "ADMIN1"


@pytest.mark.django_db
def test_bulk_deactivate_all_applies_with_valid_token(
    admin_client: Client, admin_user: object
) -> None:
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    make_mentor_periodo(matricula="22222222", creado_por=admin_user)
    make_mentor_periodo(
        matricula="33333333",
        creado_por=admin_user,
        fecha_baja=timezone.now() - timedelta(days=10),
    )
    token = _bulk_token("all", [])
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"), {"token": token}
    )
    assert response.status_code == 302
    # 11111111 + 22222222 closed; 33333333 was already closed and stays so.
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=True).count() == 0


@pytest.mark.django_db
def test_bulk_deactivate_with_tampered_token_rejects(
    admin_client: Client, admin_user: object
) -> None:
    """A token whose signature doesn't verify must be rejected with no DB writes."""
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"),
        {"token": "this.is.not-a-valid-signed-token"},
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))
    # Nothing closed.
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=True).count() == 1


@pytest.mark.django_db
def test_bulk_deactivate_with_expired_token_rejects(
    admin_client: Client, admin_user: object
) -> None:
    """Tokens expire after MAX_AGE; expired ones must not apply."""
    from unittest.mock import patch

    from django.core import signing

    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    token = _bulk_token("selected", ["11111111"])
    # Force ``signing.loads`` to behave as if the token aged past max_age.
    with patch.object(
        signing,
        "loads",
        side_effect=signing.SignatureExpired("token expired"),
    ):
        response = admin_client.post(
            reverse("mentores:deactivate_bulk"), {"token": token}
        )
    assert response.status_code == 302
    # Nothing closed.
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=True).count() == 1


@pytest.mark.django_db
def test_bulk_deactivate_token_action_must_be_known(
    admin_client: Client, admin_user: object
) -> None:
    """A signed token is necessary but not sufficient — its action must validate too."""
    make_mentor_periodo(matricula="11111111", creado_por=admin_user)
    token = _bulk_token("burn-it-all", ["11111111"])
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"), {"token": token}
    )
    assert response.status_code == 302
    assert MentorPeriodo.objects.filter(fecha_baja__isnull=True).count() == 1


@pytest.mark.django_db
def test_bulk_deactivate_step1_with_no_matriculas_for_selected_redirects(
    admin_client: Client,
) -> None:
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"),
        {"action": "selected"},  # no matriculas
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))


@pytest.mark.django_db
def test_bulk_deactivate_step1_invalid_action_redirects(
    admin_client: Client,
) -> None:
    response = admin_client.post(
        reverse("mentores:deactivate_bulk"),
        {"action": "burn-it-all"},
    )
    assert response.status_code == 302
    assert response["Location"].endswith(reverse("mentores:list"))


@pytest.mark.django_db
def test_bulk_deactivate_rejects_non_admin(alumno_client: Client) -> None:
    response = alumno_client.post(
        reverse("mentores:deactivate_bulk"), {"action": "all"}
    )
    assert response.status_code == 403
