"""Form for the CSV bulk-import view."""
from __future__ import annotations

from django import forms

MAX_BYTES = 1 * 1024 * 1024  # 1 MiB — comfortably above the largest expected catalog


class CsvImportForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo CSV",
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".csv,text/csv"}
        ),
        help_text=(
            "Una sola columna con encabezado 'matricula'. "
            "Tamaño máximo 1 MB."
        ),
    )

    def clean_archivo(self) -> bytes:
        f = self.cleaned_data["archivo"]
        if f.size > MAX_BYTES:
            raise forms.ValidationError(
                "El archivo supera el tamaño máximo permitido (1 MB)."
            )
        content: bytes = f.read()
        return content
