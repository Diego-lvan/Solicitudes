"""Runtime form builder.

Turns a frozen :class:`FormSnapshot` into a dynamically constructed Django
``Form`` class. The builder is consumed by:

- the tipos detail view (admin preview, unbound form)
- initiative 004's intake view (real submission, bound to ``request.POST``)

Both call sites get the same form shape, so an admin's preview is exactly what
the creator sees on the intake page.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django import forms

from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.formularios.validators import (
    make_extension_validator,
    make_size_validator,
)
from solicitudes.tipos.constants import FieldSource, FieldType


def field_attr_name(field_id: Any) -> str:
    """Stable form-field attribute name for a snapshot field id."""
    return f"field_{str(field_id).replace('-', '')}"


def _build_django_field(snap: FieldSnapshot) -> forms.Field:
    common: dict[str, Any] = {
        "label": snap.label,
        "required": snap.required,
        "help_text": snap.help_text or "",
    }

    if snap.field_type is FieldType.TEXT:
        return forms.CharField(
            max_length=snap.max_chars or 200,
            widget=forms.TextInput(
                attrs={"class": "form-control", "placeholder": snap.placeholder}
            ),
            **common,
        )
    if snap.field_type is FieldType.TEXTAREA:
        return forms.CharField(
            max_length=snap.max_chars or 2000,
            widget=forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": snap.placeholder,
                }
            ),
            **common,
        )
    if snap.field_type is FieldType.NUMBER:
        return forms.DecimalField(
            widget=forms.NumberInput(
                attrs={"class": "form-control", "step": "any"}
            ),
            **common,
        )
    if snap.field_type is FieldType.DATE:
        return forms.DateField(
            widget=forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            **common,
        )
    if snap.field_type is FieldType.SELECT:
        choices = [("", "---------")] + [(o, o) for o in snap.options]
        return forms.ChoiceField(
            choices=choices,
            widget=forms.Select(attrs={"class": "form-select"}),
            **common,
        )
    if snap.field_type is FieldType.FILE:
        return forms.FileField(
            validators=[
                make_extension_validator(snap.accepted_extensions),
                make_size_validator(snap.max_size_mb),
            ],
            widget=forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ",".join(snap.accepted_extensions),
                }
            ),
            **common,
        )

    # Defensive — every FieldType has a branch above. New types must extend.
    raise ValueError(f"Unsupported FieldType: {snap.field_type}")


def build_django_form(snapshot: FormSnapshot) -> type[forms.Form]:
    """Return a Form class with one field per ``snapshot.fields`` entry.

    Field attribute names are deterministic from the snapshot field id; the
    intake service in 004 uses :func:`field_attr_name` to map ``cleaned_data``
    back to ``FieldSnapshot``.
    """
    attrs: dict[str, Any] = {}
    # Auto-fill fields (source != USER_INPUT) are deliberately excluded from
    # the constructed form. Their values are resolved server-side from the
    # actor's UserDTO at intake time and merged into the persisted `valores`
    # by the intake service. Excluding them here means a malicious client
    # POSTing `field_<uuid>=...` for an auto-fill field has no form field to
    # land in, so `to_values_dict()` cannot surface it.
    user_input_fields = [
        f for f in snapshot.fields if f.source is FieldSource.USER_INPUT
    ]
    ordered = sorted(user_input_fields, key=lambda f: f.order)
    for snap in ordered:
        attrs[field_attr_name(snap.field_id)] = _build_django_field(snap)

    # Ordering on the form mirrors snapshot order so iteration in templates
    # renders fields in the admin's intended order.
    attrs["field_order"] = [field_attr_name(s.field_id) for s in ordered]

    # Helper kept on the class so callers can serialize ``cleaned_data`` to a
    # JSON-safe dict without re-deriving the attr-name mapping. Auto-fill
    # fields are absent from this map by construction (they were filtered
    # above), which is what keeps malicious client values from surfacing in
    # the dict.
    snapshots_by_attr = {
        field_attr_name(s.field_id): s for s in ordered
    }

    def to_values_dict(self: forms.Form) -> dict[str, Any]:
        """Serialize ``cleaned_data`` to JSON-safe primitives keyed by field_id.

        Decimal → str, date → ISO string. Files are not included — the intake
        service handles them through 005's storage layer.
        """
        out: dict[str, Any] = {}
        for attr, snap in snapshots_by_attr.items():
            value = self.cleaned_data.get(attr)
            if value is None:
                continue
            if snap.field_type is FieldType.NUMBER and isinstance(value, Decimal):
                out[str(snap.field_id)] = str(value)
            elif snap.field_type is FieldType.DATE and isinstance(value, date):
                out[str(snap.field_id)] = value.isoformat()
            elif snap.field_type is FieldType.FILE:
                # Files are out-of-band; record the file name only.
                out[str(snap.field_id)] = getattr(value, "name", None)
            else:
                out[str(snap.field_id)] = value
        return out

    attrs["to_values_dict"] = to_values_dict
    return type("DynamicTipoForm", (forms.Form,), attrs)
