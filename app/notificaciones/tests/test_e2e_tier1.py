"""Tier 1 cross-feature integration: lifecycle transitions emit real emails.

Wires :class:`DefaultLifecycleService` to the *real* :class:`DefaultNotificationService`
(no recording fakes) and asserts that ``mail.outbox`` receives the expected
messages. Uses Django's locmem email backend, the in-memory lifecycle / user
fakes, and exercises the same call sequence the production wiring goes through.
"""
from __future__ import annotations

import logging
from smtplib import SMTPException
from typing import cast
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from pytest_django.fixtures import SettingsWrapper

from notificaciones.services.email_sender import SmtpEmailSender
from notificaciones.services.notification_service import DefaultNotificationService
from notificaciones.services.recipient_resolver import DefaultRecipientResolver
from solicitudes.lifecycle.constants import (
    ACTION_ATENDER,
    ACTION_CANCELAR,
    Estado,
)
from solicitudes.lifecycle.notification_port import NoOpNotificationService
from solicitudes.lifecycle.schemas import TransitionInput
from solicitudes.lifecycle.services.lifecycle_service.implementation import (
    DefaultLifecycleService,
)
from solicitudes.lifecycle.tests.fakes import (
    InMemoryHistorialRepository,
    InMemorySolicitudRepository,
    empty_form_snapshot,
)
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import CreateOrUpdateUserInput, UserDTO
from usuarios.services.user_service import DefaultUserService
from usuarios.tests.fakes import (
    FakeRoleResolver,
    FakeSigaService,
    InMemoryUserRepository,
)

pytestmark = pytest.mark.django_db


def _staff(matricula: str) -> CreateOrUpdateUserInput:
    return CreateOrUpdateUserInput(
        matricula=matricula,
        email=f"{matricula.lower()}@uaz.edu.mx",
        role=Role.CONTROL_ESCOLAR,
        full_name=f"Staff {matricula}",
    )


def _alumno() -> UserDTO:
    return UserDTO(
        matricula="ALU-1",
        email="alu1@uaz.edu.mx",
        role=Role.ALUMNO,
        full_name="Ada Alumno",
    )


def _build(
    *,
    user_repo: InMemoryUserRepository,
) -> tuple[
    DefaultLifecycleService,
    InMemorySolicitudRepository,
    DefaultNotificationService,
]:
    historial = InMemoryHistorialRepository()
    solicitudes = InMemorySolicitudRepository(historial=historial)

    user_service = DefaultUserService(
        user_repository=user_repo,
        role_resolver=FakeRoleResolver(),
        siga_service=FakeSigaService(),
        logger=logging.getLogger("test.users"),
    )

    # Read-only lifecycle for the notification adapter (mirrors prod wiring).
    readonly_lifecycle = DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=NoOpNotificationService(),
    )

    notifier = DefaultNotificationService(
        lifecycle_service=readonly_lifecycle,
        recipient_resolver=DefaultRecipientResolver(user_service=user_service),
        email_sender=SmtpEmailSender(),
        logger=logging.getLogger("test.notificaciones"),
    )

    lifecycle = DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=notifier,
    )
    return lifecycle, solicitudes, notifier


def _seed_solicitud(
    repo: InMemorySolicitudRepository,
    *,
    folio: str = "SOL-2026-00001",
    estado: Estado = Estado.CREADA,
    responsible_role: Role = Role.CONTROL_ESCOLAR,
) -> str:
    from uuid import uuid4

    tipo_id = uuid4()
    detail = repo.create(
        folio=folio,
        tipo_id=tipo_id,
        solicitante_matricula="ALU-1",
        estado=estado,
        form_snapshot=empty_form_snapshot(tipo_id),
        valores={},
        requiere_pago=False,
        pago_exento=False,
    )
    repo.seed(
        detail.model_copy(
            update={
                "tipo": TipoSolicitudRow(
                    id=detail.tipo.id,
                    slug=detail.tipo.slug,
                    nombre="Constancia de estudios",
                    responsible_role=responsible_role,
                    creator_roles={Role.ALUMNO},
                    requires_payment=False,
                    activo=True,
                ),
                "solicitante": _alumno(),
            }
        )
    )
    return folio


def _staff_actor() -> UserDTO:
    return UserDTO(
        matricula="STAFF-1",
        email="staff1@uaz.edu.mx",
        role=Role.CONTROL_ESCOLAR,
        full_name="Staff Uno",
    )


def test_notify_creation_emits_one_email_per_user_with_responsible_role() -> None:
    user_repo = InMemoryUserRepository()
    user_repo.upsert(_staff("STAFF-1"))
    user_repo.upsert(_staff("STAFF-2"))
    user_repo.upsert(_staff("STAFF-3"))
    # An ALUMNO should not receive the creation fan-out.
    user_repo.upsert(
        CreateOrUpdateUserInput(
            matricula="ALU-OTHER",
            email="other@uaz.edu.mx",
            role=Role.ALUMNO,
        )
    )
    _lifecycle, solicitudes, notifier = _build(user_repo=user_repo)
    folio = _seed_solicitud(solicitudes)
    mail.outbox.clear()

    # Exercise notify_creation directly. Re-driving it through IntakeService
    # would mean wiring TipoService + mentor adapter + a freshly-built tipo
    # row — that's the responsibility of intake's own tests; here we only
    # care that the real fan-out + recipient-resolver + sender chain works.
    notifier.notify_creation(folio=folio, responsible_role=Role.CONTROL_ESCOLAR)

    # Three staff emails + one acuse de recibo to the solicitante (RF-07).
    assert sorted(m.to[0] for m in mail.outbox) == [
        "alu1@uaz.edu.mx",
        "staff-1@uaz.edu.mx",
        "staff-2@uaz.edu.mx",
        "staff-3@uaz.edu.mx",
    ]
    staff_msgs = [m for m in mail.outbox if m.to[0] != "alu1@uaz.edu.mx"]
    acuse = next(m for m in mail.outbox if m.to[0] == "alu1@uaz.edu.mx")
    assert all(
        "Nueva solicitud SOL-2026-00001" in m.subject for m in staff_msgs
    )
    assert acuse.subject == "Recibimos tu solicitud SOL-2026-00001"


def test_state_transition_emits_one_email_to_solicitante(
    settings: SettingsWrapper,
) -> None:
    settings.SITE_BASE_URL = "https://test.local"

    user_repo = InMemoryUserRepository()
    user_repo.upsert(_staff("STAFF-1"))
    lifecycle, solicitudes, _notifier = _build(user_repo=user_repo)
    folio = _seed_solicitud(solicitudes)
    mail.outbox.clear()

    lifecycle.transition(
        action=ACTION_ATENDER,
        input_dto=TransitionInput(folio=folio, actor_matricula="STAFF-1"),
        actor=_staff_actor(),
    )

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["alu1@uaz.edu.mx"]
    assert "SOL-2026-00001" in msg.subject
    assert "en proceso" in msg.subject
    # HTML alternative also populated.
    alternatives = cast(EmailMultiAlternatives, msg).alternatives
    assert alternatives and alternatives[0][1] == "text/html"
    html_body = cast(str, alternatives[0][0])
    assert "https://test.local" in html_body


def test_two_consecutive_transitions_produce_two_distinct_emails() -> None:
    user_repo = InMemoryUserRepository()
    user_repo.upsert(_staff("STAFF-1"))
    lifecycle, solicitudes, _notifier = _build(user_repo=user_repo)
    folio = _seed_solicitud(solicitudes)
    mail.outbox.clear()

    lifecycle.transition(
        action=ACTION_ATENDER,
        input_dto=TransitionInput(folio=folio, actor_matricula="STAFF-1"),
        actor=_staff_actor(),
    )
    lifecycle.transition(
        action=ACTION_CANCELAR,
        input_dto=TransitionInput(
            folio=folio,
            actor_matricula="STAFF-1",
            observaciones="Ya no la necesito",
        ),
        actor=_staff_actor(),
    )

    assert len(mail.outbox) == 2
    assert mail.outbox[0].subject != mail.outbox[1].subject
    assert "en proceso" in mail.outbox[0].subject
    assert "cancelada" in mail.outbox[1].subject
    # Self-cancel still emails the solicitante (per OQ-007 decision).
    assert mail.outbox[1].to == ["alu1@uaz.edu.mx"]
    assert "Ya no la necesito" in mail.outbox[1].body


def test_smtp_failure_does_not_block_transition_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_repo = InMemoryUserRepository()
    user_repo.upsert(_staff("STAFF-1"))
    lifecycle, solicitudes, _notifier = _build(user_repo=user_repo)
    folio = _seed_solicitud(solicitudes)
    mail.outbox.clear()

    target = "django.core.mail.message.EmailMultiAlternatives.send"
    with (
        patch(target, side_effect=SMTPException("smtp down")),
        caplog.at_level("WARNING", logger="test.notificaciones"),
    ):
        detail = lifecycle.transition(
            action=ACTION_ATENDER,
            input_dto=TransitionInput(folio=folio, actor_matricula="STAFF-1"),
            actor=_staff_actor(),
        )

    # Transition still succeeded.
    assert detail.estado is Estado.EN_PROCESO
    # Outbox unchanged because every send raised.
    assert mail.outbox == []
    # Warning carries the structured event marker + folio.
    assert any(
        "event=email_delivery_error" in r.message and folio in r.message
        for r in caplog.records
    )
