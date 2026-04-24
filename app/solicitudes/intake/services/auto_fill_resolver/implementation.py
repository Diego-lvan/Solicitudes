"""Default auto-fill resolver.

Hydrates the actor's ``UserDTO`` via :class:`UserService` once per call and
plucks the requested attributes per the source ↔ DTO mapping. Both
``resolve`` (strict) and ``preview`` (lenient) share that single hydration
call — the resolver is one round-trip per page load, regardless of how many
auto-fill fields the snapshot declares.
"""
from __future__ import annotations

from typing import Any

from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.intake.exceptions import AutoFillRequiredFieldMissing
from solicitudes.intake.services.auto_fill_resolver.interface import (
    AutoFillPreview,
    AutoFillResolver,
)
from solicitudes.tipos.constants import FieldSource
from usuarios.schemas import UserDTO
from usuarios.services.user_service.interface import UserService

# Source ↔ UserDTO attribute mapping. ``None`` is the resolver's "no value"
# sentinel — both ``""`` and ``None`` count as missing for the
# required-field check.
_SOURCE_TO_USER_ATTR: dict[FieldSource, str] = {
    FieldSource.USER_FULL_NAME: "full_name",
    FieldSource.USER_PROGRAMA: "programa",
    FieldSource.USER_EMAIL: "email",
    FieldSource.USER_MATRICULA: "matricula",
    FieldSource.USER_SEMESTRE: "semestre",
}


def _is_empty(value: Any) -> bool:
    """Match the resolver's "missing" semantics."""
    return value is None or value == ""


def _display(value: Any) -> str:
    """Render a resolved value for the read-only panel."""
    if _is_empty(value):
        return "—"
    return str(value)


class DefaultAutoFillResolver(AutoFillResolver):
    """Constructor-injected with :class:`UserService`."""

    def __init__(self, user_service: UserService) -> None:
        self._users = user_service

    # ---- public ----

    def resolve(
        self, snapshot: FormSnapshot, *, actor_matricula: str
    ) -> dict[str, Any]:
        auto_fields = self._auto_fields(snapshot)
        if not auto_fields:
            # Skip the SIGA round-trip entirely when no auto-fill is declared.
            return {}

        user = self._hydrate(actor_matricula)
        out: dict[str, Any] = {}
        missing_required: list[str] = []
        for snap in auto_fields:
            value = self._extract(snap.source, user)
            if _is_empty(value):
                if snap.required:
                    missing_required.append(snap.label)
                # Optional auto-fill fields with empty resolved values are
                # dropped from ``valores`` instead of persisted as ``None``
                # or ``""``. Mirrors ``DynamicTipoForm.to_values_dict()``,
                # which skips ``cleaned_data.get(attr) is None`` so the
                # JSONField never carries a nullish placeholder.
                continue
            out[str(snap.field_id)] = value

        if missing_required:
            raise AutoFillRequiredFieldMissing(
                "Required auto-fill fields missing: " + ", ".join(missing_required)
            )
        return out

    def preview(
        self, snapshot: FormSnapshot, *, actor_matricula: str
    ) -> AutoFillPreview:
        auto_fields = self._auto_fields(snapshot)
        if not auto_fields:
            return AutoFillPreview()

        user = self._hydrate(actor_matricula)
        items: list[tuple[str, str]] = []
        has_missing = False
        for snap in auto_fields:
            value = self._extract(snap.source, user)
            if snap.required and _is_empty(value):
                has_missing = True
            items.append((snap.label, _display(value)))
        return AutoFillPreview(items=items, has_missing_required=has_missing)

    # ---- helpers ----

    @staticmethod
    def _auto_fields(snapshot: FormSnapshot) -> list[FieldSnapshot]:
        return [f for f in snapshot.fields if f.source is not FieldSource.USER_INPUT]

    def _hydrate(self, actor_matricula: str) -> UserDTO:
        # ``hydrate_from_siga`` is best-effort by contract — it falls back to
        # the cached UserDTO when SIGA is unavailable. The resolver does not
        # need its own try/except because the contract is enforced upstream.
        return self._users.hydrate_from_siga(actor_matricula)

    @staticmethod
    def _extract(source: FieldSource, user: UserDTO) -> Any:
        attr = _SOURCE_TO_USER_ATTR.get(source)
        if attr is None:
            # Defensive — every non-USER_INPUT FieldSource has a mapping. A
            # mismatch here means a new variant was added to the enum without
            # extending the table; surface it loudly rather than persisting
            # an empty value.
            raise ValueError(f"No UserDTO mapping for FieldSource={source!r}")
        return getattr(user, attr, None)
