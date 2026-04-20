"""TipoSolicitud — a catalog entry describing a kind of request.

A tipo is the template from which solicitudes are filed. It carries:
- routing metadata: who can create it (`creator_roles`), who reviews it (`responsible_role`)
- payment posture: `requires_payment`, `mentor_exempt`
- a forward reference to a PDF plantilla (resolved in 006)
- a tombstone flag (`activo`) — never hard-deleted once a solicitud exists
- an ordered list of `FieldDefinition` rows defining the dynamic intake form
"""
from __future__ import annotations

from uuid import uuid4

from django.db import models

from usuarios.constants import Role


class TipoSolicitud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    responsible_role = models.CharField(max_length=32, choices=Role.choices())
    # `creator_roles` is a small set edited rarely; JSON is simpler than M2M
    # here. The service guards against invalid values.
    creator_roles = models.JSONField(default=list)
    requires_payment = models.BooleanField(default=False)
    # Only meaningful when requires_payment=True; the service auto-clears it
    # whenever requires_payment flips back to False.
    mentor_exempt = models.BooleanField(default=False)
    # FK target lives in 006; nullable until then. We keep it as a UUIDField
    # (not JSONField) so 006 can convert it to a real ForeignKey via migration
    # without rewriting stored data.
    plantilla_id = models.UUIDField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_tiposolicitud"
        verbose_name = "tipo de solicitud"
        verbose_name_plural = "tipos de solicitud"
        indexes = [
            models.Index(fields=["activo", "responsible_role"]),
        ]
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.slug})"
