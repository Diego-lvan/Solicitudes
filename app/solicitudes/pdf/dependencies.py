"""Dependency-injection wiring for the pdf feature."""
from __future__ import annotations

from django.conf import settings

from solicitudes.lifecycle.dependencies import get_lifecycle_service
from solicitudes.pdf.repositories.plantilla import (
    OrmPlantillaRepository,
    PlantillaRepository,
)
from solicitudes.pdf.services.pdf_service import DefaultPdfService, PdfService
from solicitudes.pdf.services.plantilla_service import (
    DefaultPlantillaService,
    PlantillaService,
)
from usuarios.dependencies import get_user_service


def get_plantilla_repository() -> PlantillaRepository:
    return OrmPlantillaRepository()


def get_plantilla_service() -> PlantillaService:
    return DefaultPlantillaService(plantilla_repository=get_plantilla_repository())


def get_pdf_service() -> PdfService:
    return DefaultPdfService(
        lifecycle_service=get_lifecycle_service(),
        plantilla_repository=get_plantilla_repository(),
        user_service=get_user_service(),
        static_root=getattr(settings, "STATIC_ROOT", None) or None,
    )
