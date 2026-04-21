"""DI wiring for the intake feature."""
from __future__ import annotations

from solicitudes.intake.mentor_port import FalseMentorService, MentorService
from solicitudes.intake.services.intake_service.implementation import (
    DefaultIntakeService,
)
from solicitudes.intake.services.intake_service.interface import IntakeService
from solicitudes.lifecycle.dependencies import (
    get_folio_service,
    get_historial_repository,
    get_lifecycle_service,
    get_notification_service,
    get_solicitud_repository,
)
from solicitudes.tipos.dependencies import get_tipo_service


def get_mentor_service() -> MentorService:
    # Until 008 lands, every user is treated as non-mentor.
    return FalseMentorService()


def get_intake_service() -> IntakeService:
    return DefaultIntakeService(
        tipo_service=get_tipo_service(),
        solicitud_repository=get_solicitud_repository(),
        historial_repository=get_historial_repository(),
        folio_service=get_folio_service(),
        lifecycle_service=get_lifecycle_service(),
        notification_service=get_notification_service(),
    )
