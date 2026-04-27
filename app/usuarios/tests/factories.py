"""Test factories for usuarios models and DTOs."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from model_bakery import baker

from usuarios.constants import Role
from usuarios.models import User
from usuarios.schemas import UserDTO


def make_user(**overrides: Any) -> User:
    """Persisted ``User`` with sensible defaults; pass kwargs to override fields.

    Defaults are uuid-derived so successive calls without explicit ``matricula``
    or ``email`` never collide on the unique constraints.
    """
    token = uuid4().hex[:10].upper()
    defaults: dict[str, Any] = {
        "matricula": overrides.pop("matricula", f"M{token}"),
        "email": overrides.pop("email", f"user-{token.lower()}@uaz.edu.mx"),
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
