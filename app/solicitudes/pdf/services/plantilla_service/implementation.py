"""Default PlantillaService implementation."""
from __future__ import annotations

import logging
from uuid import UUID

from django.template import TemplateSyntaxError, engines

from solicitudes.pdf.exceptions import PlantillaTemplateError
from solicitudes.pdf.repositories.plantilla.interface import PlantillaRepository
from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)
from solicitudes.pdf.services.plantilla_service.interface import PlantillaService

logger = logging.getLogger(__name__)


class DefaultPlantillaService(PlantillaService):
    """Owns the plantilla catalog's business rules.

    Template-syntax validation happens here (not in the schema) because it
    needs the Django template engine, which is configured via Django itself
    rather than Pydantic.
    """

    def __init__(self, plantilla_repository: PlantillaRepository) -> None:
        self._repo = plantilla_repository

    # ---- reads ----

    def list(self, *, only_active: bool = False) -> list[PlantillaRow]:
        return self._repo.list(only_active=only_active)

    def get(self, plantilla_id: UUID) -> PlantillaDTO:
        return self._repo.get_by_id(plantilla_id)

    # ---- writes ----

    def create(self, input_dto: CreatePlantillaInput) -> PlantillaDTO:
        self._validate_template(input_dto.html)
        logger.info("Creating plantilla", extra={"nombre": input_dto.nombre})
        return self._repo.create(input_dto)

    def update(self, input_dto: UpdatePlantillaInput) -> PlantillaDTO:
        self._validate_template(input_dto.html)
        logger.info("Updating plantilla", extra={"plantilla_id": str(input_dto.id)})
        return self._repo.update(input_dto)

    def deactivate(self, plantilla_id: UUID) -> None:
        self._repo.deactivate(plantilla_id)
        logger.info("Deactivated plantilla", extra={"plantilla_id": str(plantilla_id)})

    # ---- helpers ----

    @staticmethod
    def _validate_template(html: str) -> None:
        """Parse the template once to surface syntax errors at save time."""
        try:
            engines["django"].from_string(html)
        except TemplateSyntaxError as exc:
            raise PlantillaTemplateError(
                field_errors={"html": [str(exc)]}
            ) from exc
