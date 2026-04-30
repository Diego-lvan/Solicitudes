"""Feature-level exceptions for the mentores app.

All inherit (transitively) from :class:`_shared.exceptions.AppError` so they
are mappable to HTTP responses by ``AppErrorMiddleware``.
"""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class MentorNotFound(NotFound):
    code = "mentor_not_found"
    user_message = "El mentor no existe."


class MentorAlreadyActive(Conflict):
    code = "mentor_already_active"
    user_message = "El alumno ya está registrado como mentor activo."


class CsvParseError(DomainValidationError):
    code = "csv_parse_error"
    user_message = "El archivo CSV tiene un formato inválido."
