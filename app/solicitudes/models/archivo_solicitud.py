"""ArchivoSolicitud — index row for a file attached to a solicitud.

A row records *what* was uploaded (original filename, content-type, size, hash)
and *where* the bytes live (``stored_path`` relative to MEDIA_ROOT). The bytes
themselves are written by ``FileStorage`` implementations; the row is inserted
inside the same DB transaction so a rollback removes the index entry and the
storage layer cleans up the temp file via an on-commit/on-rollback hook.

Two unique partial indexes guard invariants:
- one FORM archivo per (solicitud, field_id) — replacing requires the service
  to delete the prior row first
- one COMPROBANTE archivo per solicitud
"""
from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.db import models

from solicitudes.archivos.constants import ArchivoKind


class ArchivoSolicitud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    solicitud = models.ForeignKey(
        "solicitudes.Solicitud",
        on_delete=models.CASCADE,
        related_name="archivos",
    )
    # FieldDefinition.id when kind=FORM; null when kind=COMPROBANTE.
    # Not a real FK because the form is snapshotted on the solicitud and the
    # live FieldDefinition row may be edited or deleted later.
    field_id = models.UUIDField(null=True, blank=True)
    kind = models.CharField(max_length=16, choices=ArchivoKind.choices())
    original_filename = models.CharField(max_length=255)
    # Path relative to MEDIA_ROOT, e.g. "solicitudes/SOL-2026-00042/<uuid>.pdf"
    stored_path = models.CharField(max_length=500)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_archivosolicitud"
        verbose_name = "archivo de solicitud"
        verbose_name_plural = "archivos de solicitud"
        indexes = [
            models.Index(fields=["solicitud", "kind"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "field_id"],
                name="archivo_unique_per_field",
                condition=models.Q(kind="FORM"),
            ),
            models.UniqueConstraint(
                fields=["solicitud"],
                name="archivo_unique_comprobante",
                condition=models.Q(kind="COMPROBANTE"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.solicitud_id})"
