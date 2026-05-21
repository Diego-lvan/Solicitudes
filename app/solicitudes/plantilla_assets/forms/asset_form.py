"""AssetUploadForm — boundary parser for the upload modal."""
from __future__ import annotations

from django import forms
from django.core.files.uploadedfile import UploadedFile

from solicitudes.plantilla_assets.constants import (
    ALLOWED_EXT,
    ALLOWED_MIME,
    MAX_ASSET_BYTES,
)


class AssetUploadForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        min_length=2,
        max_length=120,
    )
    imagen = forms.FileField(
        label="Imagen",
    )

    def clean_nombre(self) -> str:
        value: str = self.cleaned_data["nombre"]
        value = value.strip()
        if len(value) < 2:
            raise forms.ValidationError("El nombre es muy corto.")
        return value

    def clean_imagen(self) -> UploadedFile:
        file: UploadedFile = self.cleaned_data["imagen"]
        if file.size is None or file.size > MAX_ASSET_BYTES:
            raise forms.ValidationError(
                "La imagen excede el tamaño máximo de 2 MB."
            )
        ext = "." + (file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "")
        if ext not in ALLOWED_EXT:
            raise forms.ValidationError(
                "Formato no permitido. Usa PNG, JPG o WEBP."
            )
        ctype = (file.content_type or "").lower()
        if ctype not in ALLOWED_MIME:
            raise forms.ValidationError(
                "Tipo MIME no permitido. Usa PNG, JPG o WEBP."
            )
        return file
