"""Mentor catalog model.

A mentor is a student matricula registered as exempt from the
``comprobante de pago`` requirement on tipos with ``mentor_exempt=True``.
The catalog is small and periodically refreshed by admins (manual entry or
CSV bulk upload).

The model is the only data this app owns. The ``is_mentor`` decision used by
intake reads from this table via the repository's ``exists_active`` hot path.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from mentores.constants import MentorSource


class Mentor(models.Model):
    """Single mentor entry keyed by ``matricula``.

    ``activo=False`` is a soft-delete; ``fecha_baja`` records when the entry
    was deactivated. Reactivating an entry resets ``fecha_alta`` to ``now``
    and clears ``fecha_baja`` (handled in the repository layer).
    """

    matricula = models.CharField(max_length=20, primary_key=True)
    activo = models.BooleanField(default=True)
    fuente = models.CharField(max_length=16, choices=MentorSource.choices())
    nota = models.CharField(max_length=200, blank=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)
    fecha_baja = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        app_label = "mentores"
        db_table = "mentores_mentor"
        verbose_name = "mentor"
        verbose_name_plural = "mentores"
        indexes = [models.Index(fields=["activo"])]

    def __str__(self) -> str:
        return f"{self.matricula} ({'activo' if self.activo else 'inactivo'})"
