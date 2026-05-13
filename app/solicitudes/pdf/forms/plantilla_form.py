"""Form for plantilla CRUD."""
from __future__ import annotations

from django import forms


class PlantillaForm(forms.Form):
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
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    html = forms.CharField(
        label="HTML",
        widget=forms.Textarea(
            attrs={
                "class": "form-control font-monospace",
                "rows": 20,
                "spellcheck": "false",
            }
        ),
    )
    css = forms.CharField(
        label="CSS",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control font-monospace",
                "rows": 12,
                "spellcheck": "false",
            }
        ),
    )
    activo = forms.BooleanField(
        label="Activa",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_nombre(self) -> str:
        value: str = self.cleaned_data["nombre"]
        return value.strip()

    def clean_descripcion(self) -> str:
        value: str = self.cleaned_data.get("descripcion", "")
        return value.strip()
