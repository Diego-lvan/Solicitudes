"""Form for the manual ``add mentor`` view."""
from __future__ import annotations

from django import forms

from mentores.validators import is_valid_matricula, matricula_format_message


class AddMentorForm(forms.Form):
    matricula = forms.CharField(
        label="Matrícula",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "inputmode": "numeric",
                "pattern": r"\d{8}",
                "placeholder": "12345678",
            }
        ),
    )
    nota = forms.CharField(
        label="Nota (opcional)",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_matricula(self) -> str:
        value: str = self.cleaned_data["matricula"].strip()
        if not is_valid_matricula(value):
            raise forms.ValidationError(matricula_format_message())
        return value

    def clean_nota(self) -> str:
        value: str = self.cleaned_data.get("nota", "")
        return value.strip()
