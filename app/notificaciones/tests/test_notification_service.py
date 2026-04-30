from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from notificaciones.services.notification_service import DefaultNotificationService
from notificaciones.tests.fakes import RecordingEmailSender, StubRecipientResolver
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.lifecycle.services.lifecycle_service.interface import LifecycleService
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _solicitante() -> UserDTO:
    return UserDTO(
        matricula="A1",
        email="alumno@uaz.edu.mx",
        role=Role.ALUMNO,
        full_name="Ada Lovelace",
    )


def _staff(matricula: str, email: str) -> UserDTO:
    return UserDTO(
        matricula=matricula,
        email=email,
        role=Role.CONTROL_ESCOLAR,
        full_name=f"Staff {matricula}",
    )


def _solicitud_detail(folio: str = "SOL-2026-0001", estado: Estado = Estado.CREADA) -> SolicitudDetail:
    tipo = TipoSolicitudRow(
        id=uuid4(),
        slug="constancia",
        nombre="Constancia de estudios",
        responsible_role=Role.CONTROL_ESCOLAR,
        creator_roles={Role.ALUMNO},
        requires_payment=False,
        activo=True,
    )
    return SolicitudDetail(
        folio=folio,
        tipo=tipo,
        solicitante=_solicitante(),
        estado=estado,
        form_snapshot=FormSnapshot(
            version=1,
            tipo_id=tipo.id,
            tipo_slug=tipo.slug,
            tipo_nombre=tipo.nombre,
            captured_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            fields=[],
        ),
        valores={},
        requiere_pago=False,
        pago_exento=False,
        created_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        historial=[],
    )


class _StubLifecycleService(LifecycleService):
    def __init__(self, detail: SolicitudDetail) -> None:
        self._detail = detail

    def get_detail(self, folio: str) -> SolicitudDetail:
        return self._detail

    def list_for_personal(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def list_for_solicitante(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def list_for_admin(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def iter_for_admin(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_estado(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_tipo(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_month(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    def transition(self, *_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError


def _service(
    *,
    detail: SolicitudDetail | None = None,
    recipients: list[UserDTO] | None = None,
    sender: RecordingEmailSender | None = None,
) -> tuple[DefaultNotificationService, RecordingEmailSender]:
    sender = sender or RecordingEmailSender()
    return (
        DefaultNotificationService(
            lifecycle_service=_StubLifecycleService(detail or _solicitud_detail()),
            recipient_resolver=StubRecipientResolver(
                {Role.CONTROL_ESCOLAR: recipients or []}
            ),
            email_sender=sender,
            logger=logging.getLogger("notificaciones.test"),
        ),
        sender,
    )


def test_notify_creation_sends_staff_fanout_and_solicitante_acuse() -> None:
    recipients = [_staff("C1", "c1@uaz.edu.mx"), _staff("C2", "c2@uaz.edu.mx")]
    service, sender = _service(recipients=recipients)

    service.notify_creation(folio="SOL-2026-0001", responsible_role=Role.CONTROL_ESCOLAR)

    # Two staff emails + one acuse to the solicitante.
    assert [m["to"] for m in sender.sent] == [
        "c1@uaz.edu.mx",
        "c2@uaz.edu.mx",
        "alumno@uaz.edu.mx",
    ]
    staff_msgs = sender.sent[:2]
    acuse = sender.sent[2]
    assert all(
        m["subject"] == "Nueva solicitud SOL-2026-0001: Constancia de estudios"
        for m in staff_msgs
    )
    assert acuse["subject"] == "Recibimos tu solicitud SOL-2026-0001"
    # Folio reaches every body, both alternatives.
    assert all("SOL-2026-0001" in m["html"] and "SOL-2026-0001" in m["text"] for m in sender.sent)


def test_notify_creation_with_no_staff_recipients_still_sends_acuse() -> None:
    service, sender = _service(recipients=[])
    service.notify_creation(folio="SOL-2026-0001", responsible_role=Role.CONTROL_ESCOLAR)

    # Even with no staff for the role, the solicitante still gets the acuse.
    assert [m["to"] for m in sender.sent] == ["alumno@uaz.edu.mx"]
    assert sender.sent[0]["subject"] == "Recibimos tu solicitud SOL-2026-0001"


def test_notify_creation_swallows_per_recipient_failure_and_continues() -> None:
    recipients = [_staff("C1", "c1@uaz.edu.mx"), _staff("C2", "c2@uaz.edu.mx")]
    sender = RecordingEmailSender(fail_for={"c1@uaz.edu.mx"})
    service, _ = _service(recipients=recipients, sender=sender)

    service.notify_creation(folio="SOL-2026-0001", responsible_role=Role.CONTROL_ESCOLAR)

    # C1 failed, but C2 and the acuse still went through.
    assert [m["to"] for m in sender.sent] == ["c2@uaz.edu.mx", "alumno@uaz.edu.mx"]


def test_notify_creation_swallows_acuse_failure_without_blocking() -> None:
    recipients = [_staff("C1", "c1@uaz.edu.mx")]
    sender = RecordingEmailSender(fail_for={"alumno@uaz.edu.mx"})
    service, _ = _service(recipients=recipients, sender=sender)

    service.notify_creation(folio="SOL-2026-0001", responsible_role=Role.CONTROL_ESCOLAR)

    # Staff mail still sent; the failing acuse is logged and absorbed.
    assert [m["to"] for m in sender.sent] == ["c1@uaz.edu.mx"]


def test_notify_state_change_emails_solicitante_with_estado_and_observaciones() -> None:
    detail = _solicitud_detail(estado=Estado.FINALIZADA)
    service, sender = _service(detail=detail)

    service.notify_state_change(
        folio="SOL-2026-0001",
        estado_destino=Estado.FINALIZADA,
        observaciones="Lista para recoger.",
    )

    assert len(sender.sent) == 1
    msg = sender.sent[0]
    assert msg["to"] == "alumno@uaz.edu.mx"
    assert msg["subject"] == "Tu solicitud SOL-2026-0001 ahora está finalizada"
    assert "finalizada" in msg["html"].lower()
    assert "Lista para recoger." in msg["html"]
    assert "Lista para recoger." in msg["text"]


def test_notify_state_change_swallows_delivery_failure(caplog: pytest.LogCaptureFixture) -> None:
    sender = RecordingEmailSender(fail_for={"alumno@uaz.edu.mx"})
    service, _ = _service(sender=sender)

    with caplog.at_level("WARNING", logger="notificaciones.test"):
        service.notify_state_change(
            folio="SOL-2026-0001",
            estado_destino=Estado.EN_PROCESO,
        )

    assert sender.sent == []
    assert any(
        "event=email_delivery_error" in record.message and "SOL-2026-0001" in record.message
        for record in caplog.records
    )
