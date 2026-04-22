"""Tests for the PlantillaService — focuses on template-syntax validation."""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from solicitudes.pdf.exceptions import PlantillaTemplateError
from solicitudes.pdf.repositories.plantilla.interface import PlantillaRepository
from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)
from solicitudes.pdf.services.plantilla_service import DefaultPlantillaService


class _FakeRepo(PlantillaRepository):
    def __init__(self) -> None:
        self.created: list[CreatePlantillaInput] = []
        self.updated: list[UpdatePlantillaInput] = []
        self.deactivated: list[UUID] = []

    def get_by_id(self, plantilla_id: UUID) -> PlantillaDTO:
        raise NotImplementedError

    def list(self, *, only_active: bool = False) -> list[PlantillaRow]:
        return []

    def create(self, input_dto: CreatePlantillaInput) -> PlantillaDTO:
        self.created.append(input_dto)
        return PlantillaDTO(
            id=uuid4(),
            nombre=input_dto.nombre,
            descripcion=input_dto.descripcion,
            html=input_dto.html,
            css=input_dto.css,
            activo=input_dto.activo,
        )

    def update(self, input_dto: UpdatePlantillaInput) -> PlantillaDTO:
        self.updated.append(input_dto)
        return PlantillaDTO(
            id=input_dto.id,
            nombre=input_dto.nombre,
            descripcion=input_dto.descripcion,
            html=input_dto.html,
            css=input_dto.css,
            activo=input_dto.activo,
        )

    def deactivate(self, plantilla_id: UUID) -> None:
        self.deactivated.append(plantilla_id)


def _svc() -> tuple[DefaultPlantillaService, _FakeRepo]:
    repo = _FakeRepo()
    return DefaultPlantillaService(plantilla_repository=repo), repo


def test_create_valid_template_persists() -> None:
    svc, repo = _svc()
    svc.create(
        CreatePlantillaInput(
            nombre="OK Plantilla", html="<p>{{ solicitante.nombre }}</p>", css="", descripcion=""
        )
    )
    assert len(repo.created) == 1


def test_create_invalid_template_raises_with_field_errors() -> None:
    svc, repo = _svc()
    with pytest.raises(PlantillaTemplateError) as ei:
        svc.create(
            CreatePlantillaInput(
                nombre="OK Plantilla",
                html="<p>{% if x %}</p>",  # unclosed tag
                css="",
                descripcion="",
            )
        )
    assert "html" in ei.value.field_errors
    assert repo.created == []


def test_update_invalid_template_does_not_persist() -> None:
    svc, repo = _svc()
    pid = uuid4()
    with pytest.raises(PlantillaTemplateError):
        svc.update(
            UpdatePlantillaInput(
                id=pid,
                nombre="OK Plantilla",
                html="{% bogus %}",
                css="",
                descripcion="",
            )
        )
    assert repo.updated == []


def test_deactivate_delegates_to_repo() -> None:
    svc, repo = _svc()
    pid = uuid4()
    svc.deactivate(pid)
    assert repo.deactivated == [pid]
