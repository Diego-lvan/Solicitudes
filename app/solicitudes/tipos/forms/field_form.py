"""Form for one FieldDefinition row + its FormSet."""
from __future__ import annotations

from typing import Any

from django import forms
from django.forms import formset_factory

from solicitudes.tipos.constants import MAX_FIELDS_PER_TIPO, FieldType


class FieldForm(forms.Form):
    """One row in the dynamic-fields editor."""

    # Hidden id; populated when editing an existing field so the service can
    # update in place rather than delete-and-recreate.
    field_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    label = forms.CharField(
        label="Etiqueta",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    field_type = forms.ChoiceField(
        label="Tipo",
        choices=FieldType.choices(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    required = forms.BooleanField(
        label="Obligatorio",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    # Order is hidden in the UI: cards are reordered by drag/up-down buttons,
    # and the JS rewrites this value on submit based on DOM position.
    order = forms.IntegerField(
        label="Orden",
        min_value=0,
        widget=forms.HiddenInput(),
    )
    options_csv = forms.CharField(
        label="Opciones (separadas por coma; solo para SELECT)",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    accepted_extensions_csv = forms.CharField(
        label="Extensiones aceptadas (.pdf,.zip; solo para FILE)",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    max_size_mb = forms.IntegerField(
        label="Tamaño máx. del archivo (MB)",
        required=False,
        min_value=1,
        max_value=50,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Solo aplica a campos de tipo Archivo.",
    )
    max_chars = forms.IntegerField(
        label="Largo máx. (caracteres)",
        required=False,
        min_value=1,
        max_value=2000,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Solo aplica a campos de texto.",
    )
    placeholder = forms.CharField(
        label="Texto de ejemplo dentro del campo",
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej. Juan Pérez García",
            }
        ),
        help_text=(
            "Pista en gris que verá el solicitante dentro del campo vacío "
            "(desaparece al escribir). No se guarda como respuesta."
        ),
    )
    help_text = forms.CharField(
        label="Texto de ayuda",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        if cleaned is None:  # pragma: no cover — defensive
            return {}
        ft_value = cleaned.get("field_type")
        if not ft_value:
            return cleaned
        ft = FieldType(ft_value)
        opts_csv = (cleaned.get("options_csv") or "").strip()
        exts_csv = (cleaned.get("accepted_extensions_csv") or "").strip()

        options = [s.strip() for s in opts_csv.split(",") if s.strip()] if opts_csv else []
        extensions = (
            [e.strip().lower() for e in exts_csv.split(",") if e.strip()] if exts_csv else []
        )

        if ft is FieldType.SELECT and not options:
            self.add_error(
                "options_csv",
                "Define al menos una opción para los campos de tipo SELECT.",
            )
        if ft is not FieldType.SELECT and options:
            self.add_error("options_csv", "Solo los campos SELECT usan opciones.")

        if ft is FieldType.FILE:
            if not extensions:
                self.add_error(
                    "accepted_extensions_csv",
                    "Declara las extensiones permitidas (p. ej. .pdf,.zip).",
                )
            for e in extensions:
                if not e.startswith("."):
                    self.add_error(
                        "accepted_extensions_csv",
                        "Las extensiones deben empezar con un punto (p. ej. .pdf).",
                    )
                    break
        elif extensions:
            self.add_error(
                "accepted_extensions_csv",
                "Solo los campos FILE usan extensiones.",
            )

        cleaned["options"] = options
        cleaned["accepted_extensions"] = extensions

        # Normalize per-type-only fields. The UI hides the irrelevant inputs
        # via JS, but a stale value can still arrive (e.g., the admin set
        # max_chars on a TEXT row, then changed it to NUMBER without clearing
        # the now-hidden input). Drop those values so the schema accepts them.
        if ft is not FieldType.FILE:
            cleaned["max_size_mb"] = 10
        if ft not in (FieldType.TEXT, FieldType.TEXTAREA):
            cleaned["max_chars"] = None
        return cleaned


# A formset of FieldForm rows. ``can_delete=True`` lets the admin remove rows;
# ``min_num=0`` allows a tipo with zero fields (rare but legal).
FieldFormSet = formset_factory(
    FieldForm,
    extra=0,
    min_num=0,
    max_num=MAX_FIELDS_PER_TIPO,
    validate_max=True,
    can_delete=True,
)
