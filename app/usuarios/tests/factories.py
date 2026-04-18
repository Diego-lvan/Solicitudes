"""Test factories for usuarios models and DTOs."""
from __future__ import annotations

from typing import Any

from model_bakery import baker

from usuarios.constants import Role
from usuarios.models import User
from usuarios.schemas import UserDTO


def make_user(**overrides: Any) -> User:
    """Persisted ``User`` with sensible defaults; pass kwargs to override fields."""
    defaults: dict[str, Any] = {
        "matricula": overrides.pop("matricula", baker.seq("M")),
        "email": overrides.pop("email", f"{baker.seq('user')}@uaz.edu.mx"),
        "role": overrides.pop("role", Role.ALUMNO.value),
    }
    defaults.update(overrides)
    user: User = baker.make(User, **defaults)
    return user


def make_user_dto(**overrides: Any) -> UserDTO:
    """In-memory :class:`UserDTO` with defaults for service-layer tests."""
    fields: dict[str, Any] = {
        "matricula": "A1",
        "email": "a1@uaz.edu.mx",
        "role": Role.ALUMNO,
    }
    fields.update(overrides)
    return UserDTO(**fields)
