"""Archivos-feature exceptions.

All inherit from `_shared.exceptions` so the global error middleware can map
them to HTTP responses by ``http_status``.
"""
from __future__ import annotations

from _shared.exceptions import DomainValidationError, NotFound


class ArchivoNotFound(NotFound):
    code = "archivo_not_found"
    user_message = "El archivo no existe."


class FileTooLarge(DomainValidationError):
    code = "file_too_large"
    user_message = "El archivo excede el tamaño máximo permitido."

    def __init__(
        self,
        *,
        size_bytes: int,
        max_bytes: int,
        field: str | None = None,
    ) -> None:
        super().__init__(
            f"file size {size_bytes} exceeds limit {max_bytes}",
            field_errors={field: [self.user_message]} if field else None,
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class FileExtensionNotAllowed(DomainValidationError):
    code = "file_extension_not_allowed"
    user_message = "El tipo de archivo no está permitido para este campo."

    def __init__(
        self,
        *,
        extension: str,
        allowed: tuple[str, ...] | list[str],
        field: str | None = None,
    ) -> None:
        super().__init__(
            f"extension {extension!r} not in {tuple(allowed)!r}",
            field_errors={field: [self.user_message]} if field else None,
        )
        self.extension = extension
        self.allowed = tuple(allowed)
