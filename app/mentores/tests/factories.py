"""Test factories for mentores models and DTOs."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from model_bakery import baker

from mentores.constants import MentorSource
from mentores.models import Mentor
from mentores.schemas import MentorDTO
from usuarios.constants import Role
from usuarios.models import User


def _unique_token() -> str:
    return uuid4().hex[:10].upper()


def make_admin_user(**overrides: Any) -> User:
    """Persisted ``User`` with admin role for ``creado_por`` FKs.

    Defaults use UUID-derived identifiers so multiple calls within a single
    test never collide on the ``matricula`` PK.
    """
    token = _unique_token()
    defaults: dict[str, Any] = {
        "matricula": overrides.pop("matricula", f"ADM{token}"),
        "email": overrides.pop("email", f"admin-{token.lower()}@uaz.edu.mx"),
        "role": overrides.pop("role", Role.ADMIN.value),
    }
    defaults.update(overrides)
    user: User = baker.make(User, **defaults)
    return user


def make_mentor(**overrides: Any) -> Mentor:
    """Persisted ``Mentor`` with sensible defaults."""
    creado_por = overrides.pop("creado_por", None) or make_admin_user()
    defaults: dict[str, Any] = {
        "matricula": overrides.pop("matricula", f"M{_unique_token()}"),
        "activo": overrides.pop("activo", True),
        "fuente": overrides.pop("fuente", MentorSource.MANUAL.value),
        "nota": overrides.pop("nota", ""),
        "creado_por": creado_por,
    }
    defaults.update(overrides)
    mentor: Mentor = baker.make(Mentor, **defaults)
    return mentor


def make_mentor_dto(**overrides: Any) -> MentorDTO:
    """In-memory :class:`MentorDTO` for service-layer tests."""
    fields: dict[str, Any] = {
        "matricula": "12345678",
        "activo": True,
        "fuente": MentorSource.MANUAL,
        "nota": "",
        "fecha_alta": datetime(2026, 1, 1, tzinfo=UTC),
        "fecha_baja": None,
    }
    fields.update(overrides)
    return MentorDTO(**fields)
