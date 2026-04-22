"""Test factories for the pdf feature."""
from __future__ import annotations

from typing import Any

from model_bakery import baker

from solicitudes.models import PlantillaSolicitud


def make_plantilla(**overrides: Any) -> PlantillaSolicitud:
    """Persisted ``PlantillaSolicitud`` with sensible defaults."""
    defaults: dict[str, Any] = {
        "nombre": overrides.pop("nombre", "Constancia de Estudios"),
        "descripcion": overrides.pop("descripcion", ""),
        "html": overrides.pop(
            "html",
            "<h1>Constancia</h1><p>{{ solicitante.nombre }} ({{ solicitante.matricula }})</p>"
            "<p>Folio: {{ solicitud.folio }}</p>",
        ),
        "css": overrides.pop("css", "@page { size: A4; margin: 2cm; }"),
        "activo": overrides.pop("activo", True),
    }
    defaults.update(overrides)
    plantilla: PlantillaSolicitud = baker.make(PlantillaSolicitud, **defaults)
    return plantilla
