"""ArchivoRespuesta — one stored response file belonging to a RespuestaSolicitud batch."""
from __future__ import annotations

from uuid import uuid4

from django.db import models


class ArchivoRespuesta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    respuesta = models.ForeignKey(
        "solicitudes.RespuestaSolicitud",
        on_delete=models.CASCADE,
        related_name="archivos",
    )
    nombre_original = models.CharField(max_length=255)
    # Path relative to MEDIA_ROOT, e.g. "solicitudes/SOL-2026-00042/<uuid>.pdf"
    stored_path = models.CharField(max_length=500)
    content_type = models.CharField(max_length=120)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_archivorespuesta"
        verbose_name = "archivo de respuesta"
        verbose_name_plural = "archivos de respuesta"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["respuesta", "created_at"])]

    def __str__(self) -> str:
        return f"{self.nombre_original} ({self.respuesta_id})"
