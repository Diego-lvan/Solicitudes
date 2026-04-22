"""Sanity tests for the pdf feature exception hierarchy."""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound
from solicitudes.pdf.exceptions import (
    PlantillaNotFound,
    PlantillaTemplateError,
    TipoHasNoPlantilla,
)


def test_plantilla_not_found_is_404() -> None:
    exc = PlantillaNotFound()
    assert isinstance(exc, NotFound)
    assert exc.code == "plantilla_not_found"
    assert exc.http_status == 404


def test_template_error_carries_field_errors() -> None:
    exc = PlantillaTemplateError(field_errors={"html": ["unexpected token"]})
    assert isinstance(exc, DomainValidationError)
    assert exc.code == "plantilla_template_error"
    assert exc.http_status == 422
    assert exc.field_errors == {"html": ["unexpected token"]}


def test_tipo_has_no_plantilla_is_409() -> None:
    exc = TipoHasNoPlantilla()
    assert isinstance(exc, Conflict)
    assert exc.code == "tipo_has_no_plantilla"
    assert exc.http_status == 409
