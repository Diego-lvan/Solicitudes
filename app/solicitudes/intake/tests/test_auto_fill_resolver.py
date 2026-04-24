"""Unit tests for ``DefaultAutoFillResolver``.

The resolver depends only on a ``UserService``-shaped object; tests stub it
in-memory so they're pure-Python (no DB / no network).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.intake.exceptions import AutoFillRequiredFieldMissing
from solicitudes.intake.services.auto_fill_resolver.implementation import (
    DefaultAutoFillResolver,
)
from solicitudes.tipos.constants import FieldSource, FieldType
from usuarios.constants import Role
from usuarios.schemas import UserDTO
from usuarios.services.user_service.interface import UserService


class _StubUserService(UserService):
    """Returns a fixed :class:`UserDTO` from ``hydrate_from_siga``."""

    def __init__(self, user: UserDTO) -> None:
        self._user = user
        self.hydrate_calls: list[str] = []

    def hydrate_from_siga(self, matricula: str) -> UserDTO:
        self.hydrate_calls.append(matricula)
        return self._user

    # Unused by the resolver; raise to surface misuse.
    def get_or_create_from_claims(self, claims: Any) -> UserDTO:  # pragma: no cover
        raise NotImplementedError

    def get_by_matricula(self, matricula: str) -> UserDTO:  # pragma: no cover
        raise NotImplementedError

    def list_by_role(self, role: Role) -> list[UserDTO]:  # pragma: no cover
        raise NotImplementedError


def _user(**overrides: Any) -> UserDTO:
    base: dict[str, Any] = {
        "matricula": "ALU-1",
        "email": "alu1@uaz.edu.mx",
        "role": Role.ALUMNO,
        "full_name": "Ana Alumno",
        "programa": "Ingeniería de Software",
        "semestre": 5,
    }
    base.update(overrides)
    return UserDTO(**base)


def _snap(*fields: FieldSnapshot) -> FormSnapshot:
    return FormSnapshot(
        tipo_id=uuid4(),
        tipo_slug="t",
        tipo_nombre="T",
        captured_at=datetime.now(tz=UTC),
        fields=list(fields),
    )


def _field(
    label: str,
    source: FieldSource,
    *,
    required: bool = True,
    field_type: FieldType = FieldType.TEXT,
    order: int = 0,
) -> FieldSnapshot:
    return FieldSnapshot(
        field_id=uuid4(),
        label=label,
        field_type=field_type,
        required=required,
        order=order,
        source=source,
    )


# ---- resolve (strict) ----------------------------------------------------


def test_resolve_returns_empty_when_no_auto_fill_fields() -> None:
    users = _StubUserService(_user())
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field("Motivo", FieldSource.USER_INPUT, field_type=FieldType.TEXT, order=0)
    )
    out = resolver.resolve(snap, actor_matricula="ALU-1")
    assert out == {}
    # No SIGA round-trip when nothing to auto-fill.
    assert users.hydrate_calls == []


def test_resolve_emits_value_per_auto_fill_field() -> None:
    users = _StubUserService(_user())
    resolver = DefaultAutoFillResolver(user_service=users)
    f_prog = _field("Programa", FieldSource.USER_PROGRAMA, order=0)
    f_full = _field("Nombre", FieldSource.USER_FULL_NAME, order=1)
    f_sem = _field(
        "Semestre",
        FieldSource.USER_SEMESTRE,
        field_type=FieldType.NUMBER,
        order=2,
    )
    out = resolver.resolve(_snap(f_prog, f_full, f_sem), actor_matricula="ALU-1")
    assert out == {
        str(f_prog.field_id): "Ingeniería de Software",
        str(f_full.field_id): "Ana Alumno",
        str(f_sem.field_id): 5,
    }
    assert users.hydrate_calls == ["ALU-1"]  # one round-trip total


def test_resolve_raises_when_required_field_resolves_empty() -> None:
    users = _StubUserService(_user(programa=""))
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field("Programa", FieldSource.USER_PROGRAMA, required=True, order=0)
    )
    with pytest.raises(AutoFillRequiredFieldMissing):
        resolver.resolve(snap, actor_matricula="ALU-1")


def test_resolve_drops_optional_missing_field_from_output() -> None:
    """Optional auto-fill fields with empty resolved values are dropped
    from ``valores`` instead of persisted as ``""`` / ``None`` — keeps the
    JSONField shape consistent with ``DynamicTipoForm.to_values_dict()``,
    which also skips ``cleaned_data.get(attr) is None``."""
    users = _StubUserService(_user(programa=""))
    resolver = DefaultAutoFillResolver(user_service=users)
    f_prog = _field("Programa", FieldSource.USER_PROGRAMA, required=False, order=0)
    out = resolver.resolve(_snap(f_prog), actor_matricula="ALU-1")
    assert out == {}


def test_resolve_handles_semestre_none_as_missing_for_required() -> None:
    users = _StubUserService(_user(semestre=None))
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field(
            "Semestre",
            FieldSource.USER_SEMESTRE,
            required=True,
            field_type=FieldType.NUMBER,
            order=0,
        )
    )
    with pytest.raises(AutoFillRequiredFieldMissing):
        resolver.resolve(snap, actor_matricula="ALU-1")


# ---- preview (lenient) ---------------------------------------------------


def test_preview_returns_empty_when_no_auto_fill_fields() -> None:
    users = _StubUserService(_user())
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(_field("Motivo", FieldSource.USER_INPUT, order=0))
    preview = resolver.preview(snap, actor_matricula="ALU-1")
    assert preview.items == []
    assert preview.has_missing_required is False
    assert users.hydrate_calls == []


def test_preview_returns_labeled_pairs_for_resolved_fields() -> None:
    users = _StubUserService(_user())
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field("Programa académico", FieldSource.USER_PROGRAMA, order=0),
        _field("Nombre completo", FieldSource.USER_FULL_NAME, order=1),
    )
    preview = resolver.preview(snap, actor_matricula="ALU-1")
    assert preview.items == [
        ("Programa académico", "Ingeniería de Software"),
        ("Nombre completo", "Ana Alumno"),
    ]
    assert preview.has_missing_required is False


def test_preview_flags_missing_required_and_renders_emdash() -> None:
    users = _StubUserService(_user(programa=""))
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field("Programa", FieldSource.USER_PROGRAMA, required=True, order=0),
        _field("Nombre", FieldSource.USER_FULL_NAME, required=False, order=1),
    )
    preview = resolver.preview(snap, actor_matricula="ALU-1")
    assert preview.has_missing_required is True
    assert preview.items[0] == ("Programa", "—")
    assert preview.items[1] == ("Nombre", "Ana Alumno")


def test_preview_does_not_raise_on_missing_required() -> None:
    """The lenient path is the contract that lets the GET handler render
    the page even when SIGA was empty for a required auto-fill field."""
    users = _StubUserService(_user(programa=""))
    resolver = DefaultAutoFillResolver(user_service=users)
    snap = _snap(
        _field("Programa", FieldSource.USER_PROGRAMA, required=True, order=0)
    )
    # Should not raise.
    resolver.preview(snap, actor_matricula="ALU-1")
