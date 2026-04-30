"""SMTP-backed :class:`EmailSender` using Django's mail framework.

Uses ``EmailMultiAlternatives`` so every message ships both a plain-text body
and an HTML alternative. The actual transport is whatever ``EMAIL_BACKEND``
points at — SMTP in dev/prod, locmem in tests — so the same implementation
works everywhere and tests can introspect ``mail.outbox`` directly.
"""
from __future__ import annotations

from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from notificaciones.exceptions import EmailDeliveryError
from notificaciones.services.email_sender.interface import EmailSender


class SmtpEmailSender(EmailSender):
    def send(self, *, subject: str, to: str, html: str, text: str) -> None:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        message.attach_alternative(html, "text/html")
        try:
            message.send(fail_silently=False)
        except (TimeoutError, SMTPException, OSError) as exc:
            raise EmailDeliveryError(f"failed to deliver email to {to}: {exc}") from exc
