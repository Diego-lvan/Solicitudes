"""Outbound port for emitting notifications about solicitud transitions.

The ABC is defined here (the consumer) per the cross-feature dependency rule:
the lifecycle service depends on a port it owns, and the future
``notificaciones`` feature (007) will provide the concrete adapter. Until
then, ``NoOpNotificationService`` is wired in ``dependencies.py`` so 004 ships
standalone.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from solicitudes.lifecycle.constants import Estado
from usuarios.constants import Role


class NotificationService(ABC):
    """Notify side-channels about solicitud lifecycle events."""

    @abstractmethod
    def notify_creation(self, *, folio: str, responsible_role: Role) -> None:
        """Fired right after a solicitud is created (``CREADA`` insert)."""

    @abstractmethod
    def notify_state_change(
        self,
        *,
        folio: str,
        estado_destino: Estado,
        observaciones: str = "",
    ) -> None:
        """Fired after every successful state transition."""


class NoOpNotificationService(NotificationService):
    """Default binding until 007 lands. Does nothing."""

    def notify_creation(self, *, folio: str, responsible_role: Role) -> None:
        return None

    def notify_state_change(
        self,
        *,
        folio: str,
        estado_destino: Estado,
        observaciones: str = "",
    ) -> None:
        return None
