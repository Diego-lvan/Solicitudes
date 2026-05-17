"""RespuestaSolicitud — handler-uploaded batch of response files + comment.

Created during ``EN_PROCESO`` by personal in the responsible role (or admin).
Append-only at the application layer — there is no service method or view to
delete a batch. Django admin remains the escape hatch for exceptional cases.

Each batch can carry 0..10 files (``ArchivoRespuesta`` children) and an
optional comentario (≤2000 chars). The batch as a whole must have at least
one file OR a non-empty comment; that invariant is enforced at the
service/form layer, not the DB.
"""
from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.db import models

from usuarios.constants import Role


class RespuestaSolicitud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    solicitud = models.ForeignKey(
        "solicitudes.Solicitud",
        on_delete=models.CASCADE,
        related_name="respuestas",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actor_role = models.CharField(max_length=32, choices=Role.choices())
    comentario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_respuestasolicitud"
        verbose_name = "respuesta de solicitud"
        verbose_name_plural = "respuestas de solicitud"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["solicitud", "created_at"])]

    def __str__(self) -> str:
        return f"Respuesta {self.id} ({self.solicitud_id})"
