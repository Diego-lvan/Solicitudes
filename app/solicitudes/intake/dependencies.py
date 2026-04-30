"""DI wiring for the intake feature."""
from __future__ import annotations

from mentores.dependencies import get_intake_mentor_adapter
from solicitudes.intake.mentor_port import MentorService
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
    # Real binding (008): the adapter lives on the producer side
    # (`mentores.adapters.intake_adapter.MentoresIntakeAdapter`) per the
    # cross-feature dependency rule — intake's runtime code never imports
    # `mentores.*`; only this wiring file does, and only at boot.
    # `FalseMentorService` remains in `mentor_port.py` as a doc-only fallback
    # for tests that want to bypass the catalog entirely.
    return get_intake_mentor_adapter()


def get_intake_service() -> IntakeService:
    return DefaultIntakeService(
        tipo_service=get_tipo_service(),
        solicitud_repository=get_solicitud_repository(),
        historial_repository=get_historial_repository(),
        folio_service=get_folio_service(),
        lifecycle_service=get_lifecycle_service(),
        notification_service=get_notification_service(),
    )
