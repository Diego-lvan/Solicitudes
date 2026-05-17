"""Respuesta-feature exceptions.

All inherit from :mod:`_shared.exceptions` so the global error middleware can
map them to HTTP responses by ``http_status``.
"""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class RespuestaNotFound(NotFound):
    code = "respuesta_not_found"
    user_message = "El envío de respuesta no existe."


class ArchivoRespuestaNotFound(NotFound):
    code = "archivo_respuesta_not_found"
    user_message = "El archivo de respuesta no existe."


class InvalidStateForRespuesta(Conflict):
    code = "invalid_state_for_respuesta"
    user_message = "La solicitud debe estar En proceso para adjuntar respuesta."


class TooManyFilesInBatch(DomainValidationError):
    code = "too_many_files_in_batch"
    user_message = "Máximo 10 archivos por envío."

    def __init__(self, *, count: int, max_count: int) -> None:
        super().__init__(
            f"batch has {count} files, max is {max_count}",
            field_errors={"archivos": [self.user_message]},
        )
        self.count = count
        self.max_count = max_count


class EmptyRespuestaBatch(DomainValidationError):
    code = "empty_respuesta_batch"
    user_message = "Adjunta al menos un archivo o escribe un comentario."

    def __init__(self) -> None:
        super().__init__(
            "batch has no files and no comentario",
            field_errors={"__all__": [self.user_message]},
        )


class ResponseFileTooLarge(DomainValidationError):
    code = "response_file_too_large"
    user_message = "El archivo de respuesta excede el tamaño máximo permitido."

    def __init__(self, *, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"response file size {size_bytes} exceeds limit {max_bytes}",
            field_errors={"archivos": [self.user_message]},
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class ResponseFileExtensionNotAllowed(DomainValidationError):
    code = "response_file_extension_not_allowed"
    user_message = "El tipo de archivo de respuesta no está permitido."

    def __init__(self, *, extension: str, allowed: tuple[str, ...]) -> None:
        super().__init__(
            f"response file extension {extension!r} not in {allowed!r}",
            field_errors={"archivos": [self.user_message]},
        )
        self.extension = extension
        self.allowed = allowed
