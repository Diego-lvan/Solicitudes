"""Form for the tipo metadata (header section of create/edit)."""
from __future__ import annotations

from django import forms

from solicitudes.tipos.constants import (
    ALLOWED_CREATOR_ROLES,
    ALLOWED_RESPONSIBLE_ROLES,
)


class TipoForm(forms.Form):
    """Header form: catalog metadata only. Fields are handled by FieldFormSet."""

    nombre = forms.CharField(
        label="Nombre",
        min_length=3,
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    descripcion = forms.CharField(
        label="Descripción",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    responsible_role = forms.ChoiceField(
        label="Rol responsable de revisión",
        choices=[(r, r.replace("_", " ").title()) for r in ALLOWED_RESPONSIBLE_ROLES],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    creator_roles = forms.MultipleChoiceField(
        label="Roles que pueden crear solicitudes de este tipo",
        choices=[(r, r.title()) for r in ALLOWED_CREATOR_ROLES],
        widget=forms.CheckboxSelectMultiple,
    )
    requires_payment = forms.BooleanField(
        label="Requiere pago",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    mentor_exempt = forms.BooleanField(
        label="Mentores exentos del pago",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Solo aplica cuando el tipo requiere pago.",
    )

    def clean_nombre(self) -> str:
        value: str = self.cleaned_data["nombre"]
        return value.strip()

    def clean_descripcion(self) -> str:
        value: str = self.cleaned_data.get("descripcion", "")
        return value.strip()
