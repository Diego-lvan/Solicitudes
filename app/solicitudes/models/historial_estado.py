"""HistorialEstado — append-only state-transition log per solicitud.

Each row records: the prior estado (or ``None`` for the initial CREADA insert),
the new estado, the actor who triggered the transition, the actor's role at
that moment (snapshot, so role changes later do not rewrite history), and
optional observaciones supplied by the actor.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from solicitudes.lifecycle.constants import Estado
from usuarios.constants import Role


class HistorialEstado(models.Model):
    id = models.BigAutoField(primary_key=True)
    solicitud = models.ForeignKey(
        "solicitudes.Solicitud",
        on_delete=models.CASCADE,
        related_name="historial",
    )
    # NULL only for the initial CREADA insert at solicitud creation.
    estado_anterior = models.CharField(
        max_length=16, choices=Estado.choices(), null=True, blank=True
    )
    estado_nuevo = models.CharField(max_length=16, choices=Estado.choices())
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actor_role = models.CharField(max_length=32, choices=Role.choices())
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_historialestado"
        verbose_name = "entrada de historial"
        verbose_name_plural = "historial de estados"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["solicitud", "-created_at"])]

    def __str__(self) -> str:
        prev = self.estado_anterior or "∅"
        return f"{self.solicitud_id}: {prev} → {self.estado_nuevo}"
