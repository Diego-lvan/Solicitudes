"""Feature-level exceptions for the notificaciones app."""
from __future__ import annotations

from _shared.exceptions import ExternalServiceError


class EmailDeliveryError(ExternalServiceError):
    code = "email_delivery_error"
    user_message = "No fue posible enviar el correo de notificación."
