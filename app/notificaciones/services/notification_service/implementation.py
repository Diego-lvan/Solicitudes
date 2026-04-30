"""Default :class:`NotificationService` — wires recipient lookup + email sending.

The port is owned by the *consumer* feature (lifecycle), per the cross-feature
dependency rule. This module provides the production binding.

Failure policy: every send is wrapped; ``EmailDeliveryError`` is logged and
swallowed. RF-07 says SMTP outages must never block the underlying state
change, so callers (intake / lifecycle / revision services) treat
notifications as best-effort.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping

from django.conf import settings
from django.template.loader import render_to_string

from notificaciones.exceptions import EmailDeliveryError
from notificaciones.services.email_sender.interface import EmailSender
from notificaciones.services.recipient_resolver.interface import RecipientResolver
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.services.lifecycle_service.interface import LifecycleService
from usuarios.constants import Role

_ESTADO_LABELS: dict[Estado, str] = {
    Estado.CREADA: "creada",
    Estado.EN_PROCESO: "en proceso",
    Estado.FINALIZADA: "finalizada",
    Estado.CANCELADA: "cancelada",
}


class DefaultNotificationService(NotificationService):
    def __init__(
        self,
        *,
        lifecycle_service: LifecycleService,
        recipient_resolver: RecipientResolver,
        email_sender: EmailSender,
        logger: logging.Logger,
    ) -> None:
        self._lifecycle = lifecycle_service
        self._resolver = recipient_resolver
        self._sender = email_sender
        self._logger = logger

    def notify_creation(self, *, folio: str, responsible_role: Role) -> None:
        solicitud = self._lifecycle.get_detail(folio)

        # Fan out the "nueva solicitud" mail to every active staff with the
        # responsible role.
        recipients = self._resolver.resolve_by_role(responsible_role)
        staff_subject = f"Nueva solicitud {solicitud.folio}: {solicitud.tipo.nombre}"
        for recipient in recipients:
            self._send_one(
                template_base="notificaciones/email/nueva_solicitud",
                subject=staff_subject,
                to=recipient.email,
                context={"solicitud": solicitud, "recipient": recipient},
                folio=folio,
            )

        # Acuse de recibo to the solicitante (RF-07).
        if solicitud.solicitante.email:
            self._send_one(
                template_base="notificaciones/email/acuse_recibo",
                subject=f"Recibimos tu solicitud {solicitud.folio}",
                to=solicitud.solicitante.email,
                context={"solicitud": solicitud},
                folio=folio,
            )

    def notify_state_change(
        self,
        *,
        folio: str,
        estado_destino: Estado,
        observaciones: str = "",
    ) -> None:
        solicitud = self._lifecycle.get_detail(folio)
        estado_label = _ESTADO_LABELS.get(estado_destino, estado_destino.value)
        subject = f"Tu solicitud {solicitud.folio} ahora está {estado_label}"
        context = {
            "solicitud": solicitud,
            "estado_label": estado_label,
            "observaciones": observaciones,
        }
        self._send_one(
            template_base="notificaciones/email/estado_cambiado",
            subject=subject,
            to=solicitud.solicitante.email,
            context=context,
            folio=folio,
        )

    def _send_one(
        self,
        *,
        template_base: str,
        subject: str,
        to: str,
        context: Mapping[str, object],
        folio: str,
    ) -> None:
        full_context = {**context, "SITE_BASE_URL": settings.SITE_BASE_URL}
        html = render_to_string(f"{template_base}.html", full_context)
        text = render_to_string(f"{template_base}.txt", full_context)
        try:
            self._sender.send(subject=subject, to=to, html=html, text=text)
        except EmailDeliveryError as exc:
            # RF-07: never block the caller. Log and continue.
            self._logger.warning(
                "event=email_delivery_error folio=%s to=%s reason=%s",
                folio,
                to,
                exc,
            )

