"""Exceptions raised by the tipos feature.

Note: there is no ``TipoInUse`` exception. The catalog only supports
soft-delete (``deactivate``); hard-delete is intentionally not part of the
service surface, so the "in-use" gate has no caller. If a future need brings
back hard-delete, add the exception alongside the new operation.
"""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class TipoNotFound(NotFound):
    code = "tipo_not_found"
    user_message = "El tipo de solicitud no existe."


class TipoSlugConflict(Conflict):
    code = "tipo_slug_conflict"
    user_message = "Ya existe un tipo con ese identificador."


class InvalidFieldDefinition(DomainValidationError):
    code = "invalid_field_definition"
    user_message = "La definición del campo no es válida."
