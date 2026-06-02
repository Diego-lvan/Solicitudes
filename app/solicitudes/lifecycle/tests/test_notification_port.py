"""Tests for the default no-op notification adapter."""
from __future__ import annotations

from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.notification_port import NoOpNotificationService
from usuarios.constants import Role


def test_noop_notify_creation_is_silent() -> None:
    service = NoOpNotificationService()
    assert (
        service.notify_creation(folio="ABC-1", responsible_role=Role.CONTROL_ESCOLAR)
        is None
    )


def test_noop_notify_state_change_is_silent() -> None:
    service = NoOpNotificationService()
    assert (
        service.notify_state_change(
            folio="ABC-1", estado_destino=Estado.EN_PROCESO, observaciones="x"
        )
        is None
    )
