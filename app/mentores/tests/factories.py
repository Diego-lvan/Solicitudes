"""Test factories for mentores models and DTOs."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from django.utils import timezone
from model_bakery import baker

from mentores.constants import MentorSource
from mentores.models import MentorPeriodo
from mentores.schemas import MentorPeriodoDTO
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


def make_mentor_periodo(**overrides: Any) -> MentorPeriodo:
    """Persisted ``MentorPeriodo`` with sensible defaults.

    Default period is open (``fecha_baja=None``). Pass ``fecha_baja`` to
    create a closed period.
    """
    creado_por = overrides.pop("creado_por", None) or make_admin_user()
    defaults: dict[str, Any] = {
        "matricula": overrides.pop("matricula", f"M{_unique_token()}"),
        "fuente": overrides.pop("fuente", MentorSource.MANUAL.value),
        "nota": overrides.pop("nota", ""),
        "fecha_alta": overrides.pop("fecha_alta", timezone.now()),
        "fecha_baja": overrides.pop("fecha_baja", None),
        "creado_por": creado_por,
        "desactivado_por": overrides.pop("desactivado_por", None),
    }
    defaults.update(overrides)
    periodo: MentorPeriodo = baker.make(MentorPeriodo, **defaults)
    return periodo


def make_mentor_periodo_dto(**overrides: Any) -> MentorPeriodoDTO:
    """In-memory :class:`MentorPeriodoDTO` for service-layer tests."""
    fields: dict[str, Any] = {
        "id": 1,
        "matricula": "12345678",
        "fuente": MentorSource.MANUAL,
        "nota": "",
        "fecha_alta": datetime(2026, 1, 1, tzinfo=UTC),
        "fecha_baja": None,
        "creado_por_matricula": "ADM00000001",
        "desactivado_por_matricula": None,
    }
    fields.update(overrides)
    return MentorPeriodoDTO(**fields)
