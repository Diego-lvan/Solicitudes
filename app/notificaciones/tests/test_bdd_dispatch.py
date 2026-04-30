"""BDD scenarios for the email-dispatch flow of the notificaciones app.

Covers the happy path (state transition emits one email to the solicitante)
and an alternate path (SMTP failure does not break the transition).

Reuses the in-memory fakes already exercised in ``test_e2e_tier1.py`` so
the BDD layer drives the same wiring as production.
"""
from __future__ import annotations

import logging
from smtplib import SMTPException
from typing import cast
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from pytest_bdd import given, parsers, scenarios, then, when

from notificaciones.services.email_sender import SmtpEmailSender
from notificaciones.services.notification_service import DefaultNotificationService
from notificaciones.services.recipient_resolver import DefaultRecipientResolver
from solicitudes.lifecycle.constants import ACTION_ATENDER, Estado
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

scenarios("features/dispatch.feature")


# --- shared context -----------------------------------------------------


@pytest.fixture
def ctx() -> dict[str, object]:
    return {}


# --- Antecedentes -------------------------------------------------------


@given(
    parsers.parse(
        'un solicitante "{full_name}" con matrícula "{matricula}" y email "{email}"'
    )
)
def _given_solicitante(
    ctx: dict[str, object], full_name: str, matricula: str, email: str
) -> None:
    user_repo = InMemoryUserRepository()
    user_repo.upsert(
        CreateOrUpdateUserInput(
            matricula=matricula,
            email=email,
            role=Role.ALUMNO,
            full_name=full_name,
        )
    )
    ctx["user_repo"] = user_repo
    ctx["solicitante_email"] = email
    ctx["solicitante_matricula"] = matricula


@given("tres usuarios staff con rol Control Escolar")
def _given_staff(ctx: dict[str, object]) -> None:
    user_repo = cast(InMemoryUserRepository, ctx["user_repo"])
    for n in (1, 2, 3):
        user_repo.upsert(
            CreateOrUpdateUserInput(
                matricula=f"STAFF-{n}",
                email=f"staff-{n}@uaz.edu.mx",
                role=Role.CONTROL_ESCOLAR,
                full_name=f"Staff {n}",
            )
        )


@given(
    parsers.parse(
        'una solicitud creada con folio "{folio}" en estado CREADA'
    )
)
def _given_solicitud(ctx: dict[str, object], folio: str) -> None:
    user_repo = cast(InMemoryUserRepository, ctx["user_repo"])

    historial = InMemoryHistorialRepository()
    solicitudes = InMemorySolicitudRepository(historial=historial)

    user_service = DefaultUserService(
        user_repository=user_repo,
        role_resolver=FakeRoleResolver(),
        siga_service=FakeSigaService(),
        logger=logging.getLogger("test.users"),
    )

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

    from uuid import uuid4

    tipo_id = uuid4()
    detail = solicitudes.create(
        folio=folio,
        tipo_id=tipo_id,
        solicitante_matricula=cast(str, ctx["solicitante_matricula"]),
        estado=Estado.CREADA,
        form_snapshot=empty_form_snapshot(tipo_id),
        valores={},
        requiere_pago=False,
        pago_exento=False,
    )
    solicitudes.seed(
        detail.model_copy(
            update={
                "tipo": TipoSolicitudRow(
                    id=detail.tipo.id,
                    slug=detail.tipo.slug,
                    nombre="Constancia de estudios",
                    responsible_role=Role.CONTROL_ESCOLAR,
                    creator_roles={Role.ALUMNO},
                    requires_payment=False,
                    activo=True,
                ),
                "solicitante": UserDTO(
                    matricula=cast(str, ctx["solicitante_matricula"]),
                    email=cast(str, ctx["solicitante_email"]),
                    role=Role.ALUMNO,
                    full_name="Ada Alumno",
                ),
            }
        )
    )

    ctx["lifecycle"] = lifecycle
    ctx["solicitudes"] = solicitudes
    ctx["folio"] = folio
    mail.outbox.clear()


@given("que el backend SMTP fallará en el próximo envío")
def _given_smtp_will_fail(ctx: dict[str, object]) -> None:
    target = "django.core.mail.message.EmailMultiAlternatives.send"
    ctx["smtp_patch"] = patch(target, side_effect=SMTPException("smtp down"))


# --- When ---------------------------------------------------------------


@when(parsers.parse('el staff "{matricula}" atiende la solicitud'))
def _when_atender(
    ctx: dict[str, object],
    matricula: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lifecycle = cast(DefaultLifecycleService, ctx["lifecycle"])
    actor = UserDTO(
        matricula=matricula,
        email=f"{matricula.lower()}@uaz.edu.mx",
        role=Role.CONTROL_ESCOLAR,
        full_name=f"Actor {matricula}",
    )
    smtp_patch = ctx.get("smtp_patch")
    caplog.set_level("WARNING", logger="test.notificaciones")
    if smtp_patch is not None:
        with smtp_patch:  # type: ignore[attr-defined]
            ctx["detail"] = lifecycle.transition(
                action=ACTION_ATENDER,
                input_dto=TransitionInput(
                    folio=cast(str, ctx["folio"]), actor_matricula=matricula
                ),
                actor=actor,
            )
    else:
        ctx["detail"] = lifecycle.transition(
            action=ACTION_ATENDER,
            input_dto=TransitionInput(
                folio=cast(str, ctx["folio"]), actor_matricula=matricula
            ),
            actor=actor,
        )
    ctx["caplog"] = caplog


# --- Then ---------------------------------------------------------------


@then(
    parsers.parse(
        'se envía exactamente un correo al solicitante "{email}"'
    )
)
def _then_one_email_to(ctx: dict[str, object], email: str) -> None:
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [email]


@then(parsers.parse('el asunto del correo contiene el folio "{folio}"'))
def _then_subject_has_folio(ctx: dict[str, object], folio: str) -> None:
    assert folio in mail.outbox[0].subject


@then(parsers.parse('el asunto del correo contiene la frase "{phrase}"'))
def _then_subject_phrase(ctx: dict[str, object], phrase: str) -> None:
    assert phrase in mail.outbox[0].subject


@then("el correo incluye una alternativa HTML")
def _then_html_alt(ctx: dict[str, object]) -> None:
    msg = mail.outbox[0]
    alternatives = cast(EmailMultiAlternatives, msg).alternatives
    assert alternatives
    assert alternatives[0][1] == "text/html"


@then("la solicitud queda en estado EN_PROCESO")
def _then_in_proceso(ctx: dict[str, object]) -> None:
    detail = ctx["detail"]
    assert detail.estado is Estado.EN_PROCESO  # type: ignore[attr-defined]


@then("la bandeja de salida queda vacía")
def _then_outbox_empty(ctx: dict[str, object]) -> None:
    assert mail.outbox == []


@then(parsers.parse('se registra una advertencia con el folio "{folio}"'))
def _then_warning_logged(ctx: dict[str, object], folio: str) -> None:
    caplog = cast(pytest.LogCaptureFixture, ctx["caplog"])
    assert any(
        "event=email_delivery_error" in r.message and folio in r.message
        for r in caplog.records
    ), [r.message for r in caplog.records]
