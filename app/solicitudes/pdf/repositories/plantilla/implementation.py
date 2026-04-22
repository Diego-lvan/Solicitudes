"""ORM-backed implementation of :class:`PlantillaRepository`."""
from __future__ import annotations

from uuid import UUID

from solicitudes.models import PlantillaSolicitud
from solicitudes.pdf.exceptions import PlantillaNotFound
from solicitudes.pdf.repositories.plantilla.interface import PlantillaRepository
from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)


class OrmPlantillaRepository(PlantillaRepository):
    """Django ORM implementation. Owns all access to PlantillaSolicitud."""

    def get_by_id(self, plantilla_id: UUID) -> PlantillaDTO:
        try:
            row = PlantillaSolicitud.objects.get(pk=plantilla_id)
        except PlantillaSolicitud.DoesNotExist as exc:
            raise PlantillaNotFound(f"id={plantilla_id}") from exc
        return self._to_dto(row)

    def list(self, *, only_active: bool = False) -> list[PlantillaRow]:
        qs = PlantillaSolicitud.objects.all()
        if only_active:
            qs = qs.filter(activo=True)
        return [self._to_row(p) for p in qs]

    def create(self, input_dto: CreatePlantillaInput) -> PlantillaDTO:
        row = PlantillaSolicitud.objects.create(
            nombre=input_dto.nombre,
            descripcion=input_dto.descripcion,
            html=input_dto.html,
            css=input_dto.css,
            activo=input_dto.activo,
        )
        return self._to_dto(row)

    def update(self, input_dto: UpdatePlantillaInput) -> PlantillaDTO:
        try:
            row = PlantillaSolicitud.objects.get(pk=input_dto.id)
        except PlantillaSolicitud.DoesNotExist as exc:
            raise PlantillaNotFound(f"id={input_dto.id}") from exc
        row.nombre = input_dto.nombre
        row.descripcion = input_dto.descripcion
        row.html = input_dto.html
        row.css = input_dto.css
        row.activo = input_dto.activo
        row.save()
        return self._to_dto(row)

    def deactivate(self, plantilla_id: UUID) -> None:
        updated = PlantillaSolicitud.objects.filter(pk=plantilla_id).update(activo=False)
        if updated == 0:
            raise PlantillaNotFound(f"id={plantilla_id}")

    @staticmethod
    def _to_dto(row: PlantillaSolicitud) -> PlantillaDTO:
        return PlantillaDTO(
            id=row.id,
            nombre=row.nombre,
            descripcion=row.descripcion,
            html=row.html,
            css=row.css,
            activo=row.activo,
        )

    @staticmethod
    def _to_row(row: PlantillaSolicitud) -> PlantillaRow:
        return PlantillaRow(
            id=row.id,
            nombre=row.nombre,
            descripcion=row.descripcion,
            activo=row.activo,
        )
