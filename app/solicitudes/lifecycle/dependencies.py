"""DI wiring for the lifecycle feature."""
from __future__ import annotations

from solicitudes.lifecycle.notification_port import (
    NoOpNotificationService,
    NotificationService,
)
from solicitudes.lifecycle.repositories.folio.implementation import (
    OrmFolioRepository,
)
from solicitudes.lifecycle.repositories.folio.interface import FolioRepository
from solicitudes.lifecycle.repositories.historial.implementation import (
    OrmHistorialRepository,
)
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.implementation import (
    OrmSolicitudRepository,
)
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.services.folio_service.implementation import (
    DefaultFolioService,
)
from solicitudes.lifecycle.services.folio_service.interface import FolioService
from solicitudes.lifecycle.services.lifecycle_service.implementation import (
    DefaultLifecycleService,
)
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)


def get_folio_repository() -> FolioRepository:
    return OrmFolioRepository()


def get_historial_repository() -> HistorialRepository:
    return OrmHistorialRepository()


def get_solicitud_repository() -> SolicitudRepository:
    return OrmSolicitudRepository(historial_repository=get_historial_repository())


def get_notification_service() -> NotificationService:
    # Until 007 lands the real adapter, every notify_* call is a no-op.
    return NoOpNotificationService()


def get_folio_service() -> FolioService:
    return DefaultFolioService(folio_repository=get_folio_repository())


def get_lifecycle_service() -> LifecycleService:
    return DefaultLifecycleService(
        solicitud_repository=get_solicitud_repository(),
        historial_repository=get_historial_repository(),
        notification_service=get_notification_service(),
    )
