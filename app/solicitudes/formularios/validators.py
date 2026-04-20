"""Per-FieldType validation helpers used by the formularios builder."""
from __future__ import annotations

import os
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile


def make_extension_validator(accepted_extensions: list[str]) -> Any:
    """Return a Django validator that rejects files outside ``accepted_extensions``.

    Extensions in ``accepted_extensions`` are compared case-insensitively and
    must include the leading dot (e.g. ``[".pdf", ".zip"]``).
    """
    normalized = {e.lower() for e in accepted_extensions}

    def validate(file: UploadedFile) -> None:
        if file is None or file.name is None:
            return
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in normalized:
            raise ValidationError(
                "Extensión no permitida: solo se aceptan %(allowed)s.",
                params={"allowed": ", ".join(sorted(normalized))},
            )

    return validate


def make_size_validator(max_size_mb: int) -> Any:
    """Return a Django validator that rejects files over ``max_size_mb``."""
    max_bytes = max_size_mb * 1024 * 1024

    def validate(file: UploadedFile) -> None:
        if file is None:
            return
        if file.size is not None and file.size > max_bytes:
            raise ValidationError(
                "El archivo excede el tamaño máximo de %(mb)s MB.",
                params={"mb": max_size_mb},
            )

    return validate
