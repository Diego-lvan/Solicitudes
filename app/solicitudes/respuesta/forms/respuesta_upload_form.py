"""Form for the handler-side response upload (batch + comment)."""
from __future__ import annotations

from typing import Any

from django import forms

from solicitudes.respuesta.constants import (
    MAX_COMENTARIO_CHARS,
    MAX_FILES_PER_BATCH,
)


class _MultipleFileInput(forms.ClearableFileInput):
    """``ClearableFileInput`` with ``multiple`` enabled — Django ships the
    HTML attribute but not the field that handles a list cleanly."""

    allow_multiple_selected = True


class _MultipleFileField(forms.FileField):
    """File field that returns ``list[UploadedFile]`` instead of a single one."""

    widget = _MultipleFileInput

    def to_python(self, data: Any) -> list[Any] | None:  # type: ignore[override]
        if data in (None, ""):
            return None
        if isinstance(data, list):
            return [super(_MultipleFileField, self).to_python(item) for item in data]
        return [super().to_python(data)]


class RespuestaUploadForm(forms.Form):
    comentario = forms.CharField(
        required=False,
        max_length=MAX_COMENTARIO_CHARS,
        label="Comentario (opcional)",
        widget=forms.Textarea(
            attrs={"rows": 4, "maxlength": MAX_COMENTARIO_CHARS}
        ),
    )
    archivos = _MultipleFileField(required=False, label="Archivos de respuesta")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        files: list[Any] = []
        if self.files:
            files = list(self.files.getlist("archivos"))
        comentario = (cleaned.get("comentario") or "").strip()
        if not files and not comentario:
            raise forms.ValidationError(
                "Adjunta al menos un archivo o escribe un comentario."
            )
        if len(files) > MAX_FILES_PER_BATCH:
            raise forms.ValidationError(
                f"Máximo {MAX_FILES_PER_BATCH} archivos por envío."
            )
        cleaned["archivos_list"] = files
        cleaned["comentario"] = comentario
        return cleaned
