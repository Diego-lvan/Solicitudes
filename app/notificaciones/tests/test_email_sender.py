from __future__ import annotations

from typing import cast
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from pytest_django.fixtures import SettingsWrapper

from notificaciones.exceptions import EmailDeliveryError
from notificaciones.services.email_sender import SmtpEmailSender


@pytest.mark.django_db
def test_smtp_sender_writes_to_outbox_with_html_alternative() -> None:
    SmtpEmailSender().send(
        subject="Asunto",
        to="alumno@uaz.edu.mx",
        html="<p>Hola</p>",
        text="Hola",
    )

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "Asunto"
    assert msg.to == ["alumno@uaz.edu.mx"]
    assert msg.body == "Hola"
    assert cast(EmailMultiAlternatives, msg).alternatives == [("<p>Hola</p>", "text/html")]


def test_smtp_sender_uses_default_from_email(settings: SettingsWrapper) -> None:
    settings.DEFAULT_FROM_EMAIL = "noreply@uaz.edu.mx"

    SmtpEmailSender().send(
        subject="x",
        to="a@uaz.edu.mx",
        html="<p>x</p>",
        text="x",
    )

    assert mail.outbox[-1].from_email == "noreply@uaz.edu.mx"


def test_smtp_sender_wraps_transport_failure_in_email_delivery_error() -> None:
    from smtplib import SMTPException

    with (
        patch(
            "django.core.mail.EmailMultiAlternatives.send",
            side_effect=SMTPException("boom"),
        ),
        pytest.raises(EmailDeliveryError) as excinfo,
    ):
        SmtpEmailSender().send(subject="x", to="a@uaz.edu.mx", html="<p>x</p>", text="x")

    assert "a@uaz.edu.mx" in str(excinfo.value)
