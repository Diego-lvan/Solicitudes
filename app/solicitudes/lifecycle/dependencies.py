"""DI wiring for the lifecycle feature."""
from __future__ import annotations

import logging

from notificaciones.services.email_sender import SmtpEmailSender
from notificaciones.services.notification_service import DefaultNotificationService
from notificaciones.services.recipient_resolver import DefaultRecipientResolver
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
from usuarios.dependencies import get_user_service


def get_folio_repository() -> FolioRepository:
    return OrmFolioRepository()


def get_historial_repository() -> HistorialRepository:
    return OrmHistorialRepository()


def get_solicitud_repository() -> SolicitudRepository:
    return OrmSolicitudRepository(historial_repository=get_historial_repository())


def get_folio_service() -> FolioService:
    return DefaultFolioService(folio_repository=get_folio_repository())


def get_lifecycle_service() -> LifecycleService:
    """Production-wired lifecycle service.

    Construction is non-trivial because notifications depend on the lifecycle
    (to load ``SolicitudDetail``) while the lifecycle depends on the notifier
    (to fire on transitions). The cycle is broken by giving the notifier a
    *separate* read-only lifecycle wired with ``NoOpNotificationService``.

    Both ``LifecycleService`` instances share the same repository objects, so
    if a future change starts caching state on the repos, reads from the
    notifier and writes from the real lifecycle will not diverge.
    """
    historial = get_historial_repository()
    solicitudes = OrmSolicitudRepository(historial_repository=historial)

    readonly_lifecycle = DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=NoOpNotificationService(),
    )

    notifier: NotificationService = DefaultNotificationService(
        lifecycle_service=readonly_lifecycle,
        recipient_resolver=DefaultRecipientResolver(user_service=get_user_service()),
        email_sender=SmtpEmailSender(),
        logger=logging.getLogger("notificaciones"),
    )

    return DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=notifier,
    )


def get_notification_service() -> NotificationService:
    """Factory exposed to other features that consume ``NotificationService``.

    Returns the same wiring as :func:`get_lifecycle_service` would build for
    its notifier, so callers (intake, revision) get the same behaviour the
    real lifecycle uses.
    """
    historial = get_historial_repository()
    solicitudes = OrmSolicitudRepository(historial_repository=historial)
    readonly_lifecycle = DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=NoOpNotificationService(),
    )
    return DefaultNotificationService(
        lifecycle_service=readonly_lifecycle,
        recipient_resolver=DefaultRecipientResolver(user_service=get_user_service()),
        email_sender=SmtpEmailSender(),
        logger=logging.getLogger("notificaciones"),
    )
