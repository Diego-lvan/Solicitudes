"""In-memory fakes for reportes service tests."""
from __future__ import annotations

from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.services.lifecycle_service.implementation import (
    DefaultLifecycleService,
)
from solicitudes.lifecycle.tests.fakes import (
    InMemoryHistorialRepository,
    InMemorySolicitudRepository,
)


class _NoopNotifier(NotificationService):
    def notify_creation(self, **_kwargs: object) -> None:
        return None

    def notify_state_change(self, **_kwargs: object) -> None:
        return None


def make_in_memory_lifecycle(
    *,
    historial: InMemoryHistorialRepository | None = None,
) -> tuple[DefaultLifecycleService, InMemorySolicitudRepository]:
    """Build a lifecycle service backed by in-memory fakes."""
    historial = historial or InMemoryHistorialRepository()
    repo = InMemorySolicitudRepository(historial=historial)
    service = DefaultLifecycleService(
        solicitud_repository=repo,
        historial_repository=historial,
        notification_service=_NoopNotifier(),
    )
    return service, repo
