"""Solicitud — a filed request, a snapshot of a TipoSolicitud's form at intake.

A solicitud is keyed by its human-readable ``folio`` (``SOL-YYYY-NNNNN``) so
operators can paste a folio into a URL or an email and reach the canonical
record. The form definition that produced it is **frozen** at creation time
inside ``form_snapshot``: later edits to the live tipo never change what was
originally submitted.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from solicitudes.lifecycle.constants import Estado


class Solicitud(models.Model):
    folio = models.CharField(max_length=20, primary_key=True)
    tipo = models.ForeignKey(
        "solicitudes.TipoSolicitud",
        on_delete=models.PROTECT,
        related_name="solicitudes",
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes",
    )
    estado = models.CharField(
        max_length=16,
        choices=Estado.choices(),
        default=Estado.CREADA.value,
    )
    # Frozen FormSnapshot.model_dump(); never mutated after creation.
    form_snapshot = models.JSONField()
    # field_id (str UUID) -> primitive. Files live in ArchivoSolicitud (005).
    valores = models.JSONField(default=dict)
    # Captured at creation: the tipo's `requires_payment` and the actor's
    # mentor exemption resolution. Stored on the row (not derived) so audit
    # queries are stable and the mentor list changing later does not retro-
    # actively flip the exemption.
    requiere_pago = models.BooleanField()
    pago_exento = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_solicitud"
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        indexes = [
            models.Index(fields=["solicitante", "-created_at"]),
            models.Index(fields=["estado", "-created_at"]),
            models.Index(fields=["tipo", "estado"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.folio
