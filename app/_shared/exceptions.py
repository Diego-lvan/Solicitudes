"""Application-level exception hierarchy.

Every exception that is meant to be mapped to an HTTP response by middleware
must inherit from :class:`AppError`. Feature-specific exceptions live in each
feature's ``exceptions.py`` and subclass one of these sentinels.
"""
from __future__ import annotations


class AppError(Exception):
    """Base for all application-level exceptions."""

    code: str = "app_error"
    user_message: str = "Ocurrió un error."
    http_status: int = 500

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        self.message = message or self.user_message


class NotFound(AppError):
    code = "not_found"
    user_message = "El recurso solicitado no existe."
    http_status = 404


class Conflict(AppError):
    code = "conflict"
    user_message = "La operación entra en conflicto con el estado actual."
    http_status = 409


class Unauthorized(AppError):
    code = "unauthorized"
    user_message = "No tienes permiso para realizar esta acción."
    http_status = 403


class AuthenticationRequired(AppError):
    code = "authentication_required"
    user_message = "Inicia sesión para continuar."
    http_status = 401


class DomainValidationError(AppError):
    code = "validation_error"
    user_message = "Los datos no son válidos."
    http_status = 422

    def __init__(
        self,
        message: str | None = None,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.field_errors: dict[str, list[str]] = field_errors or {}


class ExternalServiceError(AppError):
    code = "external_service_error"
    user_message = "Un servicio externo no está disponible. Intenta más tarde."
    http_status = 502
