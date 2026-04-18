from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from usuarios.constants import Role
from usuarios.models import User


def test_auth_user_model_resolves_to_usuarios_user() -> None:
    assert get_user_model() is User


@pytest.mark.django_db
def test_user_can_be_persisted_with_minimum_fields() -> None:
    user = User.objects.create(
        matricula="A12345",
        email="alumno@uaz.edu.mx",
        role=Role.ALUMNO.value,
    )
    assert user.pk == "A12345"
    assert user.is_authenticated is True
    assert user.is_anonymous is False


@pytest.mark.django_db
def test_user_email_is_unique() -> None:
    User.objects.create(matricula="A1", email="dup@uaz.edu.mx", role=Role.ALUMNO.value)
    with pytest.raises(IntegrityError):
        User.objects.create(matricula="A2", email="dup@uaz.edu.mx", role=Role.DOCENTE.value)


@pytest.mark.django_db
def test_get_by_natural_key_uses_matricula() -> None:
    User.objects.create(matricula="NK1", email="nk@uaz.edu.mx", role=Role.ADMIN.value)
    found = User.objects.get_by_natural_key("NK1")
    assert found.matricula == "NK1"


def test_create_user_is_disabled() -> None:
    with pytest.raises(NotImplementedError):
        User.objects.create_user(matricula="x", email="x@x", role=Role.ALUMNO.value)


def test_create_superuser_is_disabled() -> None:
    with pytest.raises(NotImplementedError):
        User.objects.create_superuser(matricula="x", email="x@x", role=Role.ADMIN.value)


@pytest.mark.django_db
def test_get_full_name_falls_back_to_matricula() -> None:
    u = User.objects.create(matricula="FN1", email="fn@uaz.edu.mx", role=Role.ALUMNO.value)
    assert u.get_full_name() == "FN1"
    u.full_name = "Ada Lovelace"
    u.save()
    assert u.get_full_name() == "Ada Lovelace"
    assert u.get_short_name() == "Ada"


def test_user_meta() -> None:
    assert User._meta.db_table == "usuarios_user"
    assert User.USERNAME_FIELD == "matricula"
    assert User.REQUIRED_FIELDS == ["email", "role"]
