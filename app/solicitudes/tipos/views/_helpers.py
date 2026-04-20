"""Shared helpers for tipos admin views.

Translation between Django form data and Pydantic input DTOs lives here so
create.py and edit.py share the conversion logic.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from django.forms import BaseFormSet

from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.forms import TipoForm
from solicitudes.tipos.schemas import (
    CreateFieldInput,
    CreateTipoInput,
    UpdateTipoInput,
)
from usuarios.constants import Role


def fieldset_initial_from_dto(fields: list[Any]) -> list[dict[str, Any]]:
    """Convert a list of FieldDefinitionDTO into FieldFormSet `initial` data."""
    out: list[dict[str, Any]] = []
    for f in fields:
        out.append(
            {
                "field_id": f.id,
                "label": f.label,
                "field_type": f.field_type.value,
                "required": f.required,
                "order": f.order,
                "options_csv": ",".join(f.options),
                "accepted_extensions_csv": ",".join(f.accepted_extensions),
                "max_size_mb": f.max_size_mb,
                "max_chars": f.max_chars,
                "placeholder": f.placeholder,
                "help_text": f.help_text,
            }
        )
    return out


def build_create_input(
    tipo_form: TipoForm, formset: BaseFormSet[Any]
) -> CreateTipoInput:
    return CreateTipoInput(
        nombre=tipo_form.cleaned_data["nombre"],
        descripcion=tipo_form.cleaned_data.get("descripcion", ""),
        responsible_role=Role(tipo_form.cleaned_data["responsible_role"]),
        creator_roles={Role(r) for r in tipo_form.cleaned_data["creator_roles"]},
        requires_payment=tipo_form.cleaned_data.get("requires_payment", False),
        mentor_exempt=tipo_form.cleaned_data.get("mentor_exempt", False),
        fields=_collect_fields(formset),
    )


def build_update_input(
    tipo_id: UUID, tipo_form: TipoForm, formset: BaseFormSet[Any]
) -> UpdateTipoInput:
    return UpdateTipoInput(
        id=tipo_id,
        nombre=tipo_form.cleaned_data["nombre"],
        descripcion=tipo_form.cleaned_data.get("descripcion", ""),
        responsible_role=Role(tipo_form.cleaned_data["responsible_role"]),
        creator_roles={Role(r) for r in tipo_form.cleaned_data["creator_roles"]},
        requires_payment=tipo_form.cleaned_data.get("requires_payment", False),
        mentor_exempt=tipo_form.cleaned_data.get("mentor_exempt", False),
        fields=_collect_fields(formset),
    )


def _collect_fields(formset: BaseFormSet[Any]) -> list[CreateFieldInput]:
    """Collect non-deleted, non-empty rows from a *validated* formset.

    Precondition: the caller has already invoked ``formset.is_valid()`` and
    confirmed it returned ``True``. This helper does not silently skip
    invalid rows — that would mask user input errors. It only filters
    rows that the user explicitly marked DELETE and unfilled extra rows.
    """
    fields: list[CreateFieldInput] = []
    for sub in formset:
        if sub.cleaned_data.get("DELETE"):
            continue
        if not sub.cleaned_data:  # empty extra row
            continue
        fields.append(
            CreateFieldInput(
                id=sub.cleaned_data.get("field_id"),
                label=sub.cleaned_data["label"],
                field_type=FieldType(sub.cleaned_data["field_type"]),
                required=sub.cleaned_data.get("required", False),
                order=sub.cleaned_data["order"],
                options=sub.cleaned_data.get("options", []),
                accepted_extensions=sub.cleaned_data.get("accepted_extensions", []),
                max_size_mb=sub.cleaned_data.get("max_size_mb") or 10,
                max_chars=sub.cleaned_data.get("max_chars"),
                placeholder=sub.cleaned_data.get("placeholder", ""),
                help_text=sub.cleaned_data.get("help_text", ""),
            )
        )
    return fields
