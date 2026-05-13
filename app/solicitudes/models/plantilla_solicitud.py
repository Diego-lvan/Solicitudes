"""PlantillaSolicitud — admin-managed HTML/CSS template for rendering a
solicitud as a PDF.

Plantillas are referenced by ``TipoSolicitud.plantilla`` (FK, nullable). The
HTML body uses Django template syntax (``{{ var }}``, tags, filters). PDF
bytes are not stored — every download re-renders from the source data, so
the plantilla is the only authoring artifact.
"""
from __future__ import annotations

from uuid import uuid4

from django.db import models


class PlantillaSolicitud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    # Django-template HTML; rendered with ``Engine.from_string`` at PDF time.
    # Validated at save (``services.plantilla_service``) by parsing once.
    html = models.TextField()
    css = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_plantillasolicitud"
        verbose_name = "plantilla de solicitud"
        verbose_name_plural = "plantillas de solicitud"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["activo", "nombre"]),
        ]

    def __str__(self) -> str:
        return self.nombre
