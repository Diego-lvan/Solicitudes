"""__str__ smoke tests for the solicitudes models.

Each model defines a human-readable ``__str__`` used in the Django admin and
in logs. These tests pin the format so a refactor that breaks it is caught.
"""
from __future__ import annotations

import pytest
from model_bakery import baker

from solicitudes.models import (
    ArchivoRespuesta,
    ArchivoSolicitud,
    FieldDefinition,
    FolioCounter,
    HistorialEstado,
    PlantillaAsset,
    PlantillaSolicitud,
    RespuestaSolicitud,
    Solicitud,
    TipoSolicitud,
)


@pytest.mark.django_db
def test_tipo_solicitud_str() -> None:
    tipo = baker.make(TipoSolicitud, nombre="Constancia", slug="constancia")
    assert str(tipo) == "Constancia (constancia)"


@pytest.mark.django_db
def test_field_definition_str() -> None:
    field = baker.make(FieldDefinition, label="Motivo", field_type="TEXT")
    assert str(field) == "Motivo [TEXT]"


@pytest.mark.django_db
def test_solicitud_str_is_folio() -> None:
    sol = baker.make(Solicitud, folio="SOL-2026-00001")
    assert str(sol) == "SOL-2026-00001"


@pytest.mark.django_db
def test_historial_estado_str_with_and_without_previous() -> None:
    sol = baker.make(Solicitud, folio="SOL-2026-00002")
    with_prev = baker.make(
        HistorialEstado,
        solicitud=sol,
        estado_anterior="CREADA",
        estado_nuevo="EN_PROCESO",
    )
    assert "CREADA → EN_PROCESO" in str(with_prev)
    without_prev = baker.make(
        HistorialEstado,
        solicitud=sol,
        estado_anterior="",
        estado_nuevo="CREADA",
    )
    assert "∅ → CREADA" in str(without_prev)


@pytest.mark.django_db
def test_folio_counter_str() -> None:
    counter = baker.make(FolioCounter, year=2026, last=7)
    assert str(counter) == "2026: 7"


@pytest.mark.django_db
def test_plantilla_solicitud_str_is_nombre() -> None:
    plantilla = baker.make(PlantillaSolicitud, nombre="Constancia PDF")
    assert str(plantilla) == "Constancia PDF"


@pytest.mark.django_db
def test_plantilla_asset_str() -> None:
    asset = baker.make(PlantillaAsset, nombre="Logo", scope="global")
    assert str(asset) == "Logo (global)"


@pytest.mark.django_db
def test_archivo_solicitud_str() -> None:
    sol = baker.make(Solicitud, folio="SOL-2026-00003")
    archivo = baker.make(
        ArchivoSolicitud, solicitud=sol, original_filename="doc.pdf"
    )
    assert "doc.pdf" in str(archivo)


@pytest.mark.django_db
def test_respuesta_solicitud_str() -> None:
    sol = baker.make(Solicitud, folio="SOL-2026-00004")
    respuesta = baker.make(RespuestaSolicitud, solicitud=sol)
    assert "Respuesta" in str(respuesta)


@pytest.mark.django_db
def test_archivo_respuesta_str() -> None:
    sol = baker.make(Solicitud, folio="SOL-2026-00005")
    respuesta = baker.make(RespuestaSolicitud, solicitud=sol)
    archivo = baker.make(
        ArchivoRespuesta, respuesta=respuesta, nombre_original="reply.pdf"
    )
    assert "reply.pdf" in str(archivo)
