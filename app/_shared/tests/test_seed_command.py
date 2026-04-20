"""Tests for the ``manage.py seed`` command."""
from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from solicitudes.models import TipoSolicitud
from usuarios.constants import Role
from usuarios.models import User

# pytest-django runs tests with DEBUG=False; the seed command's safety guard
# refuses to run in that mode. The dev/test path needs DEBUG=True explicitly.
pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True)
def test_seed_creates_users_and_tipos() -> None:
    out = StringIO()
    call_command("seed", stdout=out)

    assert User.objects.count() >= 5
    assert User.objects.filter(role=Role.ADMIN.value, matricula="ADMIN_TEST").exists()
    assert TipoSolicitud.objects.filter(slug="constancia-de-estudios").exists()
    assert TipoSolicitud.objects.filter(slug="solicitud-cambio-programa").exists()
    constancia = TipoSolicitud.objects.get(slug="constancia-de-estudios")
    assert constancia.fields.count() == 3


@override_settings(DEBUG=True)
def test_seed_is_idempotent_without_fresh() -> None:
    call_command("seed")
    user_count_after_first = User.objects.count()
    constancia = TipoSolicitud.objects.get(slug="constancia-de-estudios")
    field_count_after_first = constancia.fields.count()

    call_command("seed")

    assert User.objects.count() == user_count_after_first
    constancia.refresh_from_db()
    assert constancia.fields.count() == field_count_after_first


@override_settings(DEBUG=True)
def test_seed_fresh_replaces_seeded_rows_only() -> None:
    # Pre-existing user that is *not* part of the seed set must survive --fresh.
    User.objects.create(
        matricula="HANDMADE", email="manual@uaz.edu.mx", role=Role.ALUMNO.value
    )
    call_command("seed")
    call_command("seed", "--fresh")

    assert User.objects.filter(matricula="HANDMADE").exists()
    assert User.objects.filter(matricula="ADMIN_TEST").exists()


@override_settings(DEBUG=True)
def test_seed_only_runs_one_app() -> None:
    call_command("seed", "--only", "usuarios")
    assert User.objects.filter(matricula="ADMIN_TEST").exists()
    assert not TipoSolicitud.objects.exists()


@override_settings(DEBUG=True)
def test_seed_unknown_only_raises() -> None:
    with pytest.raises(CommandError):
        call_command("seed", "--only", "doesnotexist")


@override_settings(DEBUG=False)
def test_seed_refuses_with_debug_false() -> None:
    with pytest.raises(CommandError):
        call_command("seed")


@override_settings(DEBUG=False)
def test_seed_runs_with_debug_false_under_allow_prod() -> None:
    call_command("seed", "--allow-prod")
    assert User.objects.filter(matricula="ADMIN_TEST").exists()
