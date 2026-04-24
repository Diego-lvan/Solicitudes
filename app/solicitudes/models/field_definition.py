"""FieldDefinition — one typed field in a TipoSolicitud's dynamic form."""
from __future__ import annotations

from uuid import uuid4

from django.db import models

from solicitudes.tipos.constants import FieldSource, FieldType


class FieldDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tipo = models.ForeignKey(
        "solicitudes.TipoSolicitud",
        on_delete=models.CASCADE,
        related_name="fields",
    )
    label = models.CharField(max_length=120)
    field_type = models.CharField(max_length=16, choices=FieldType.choices())
    # Where the value comes from at intake. `USER_INPUT` means the alumno
    # types it; other variants pull from the hydrated UserDTO and the form
    # builder never renders a control for them.
    source = models.CharField(
        max_length=24,
        choices=FieldSource.choices(),
        default=FieldSource.USER_INPUT.value,
    )
    required = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField()
    # `options` only applies to SELECT fields; ignored otherwise.
    options = models.JSONField(default=list, blank=True)
    # `accepted_extensions` only applies to FILE fields; ignored otherwise.
    accepted_extensions = models.JSONField(default=list, blank=True)
    # `max_size_mb` only applies to FILE; default kept for storage simplicity.
    max_size_mb = models.PositiveIntegerField(default=10)
    # `max_chars` only applies to TEXT/TEXTAREA. NULL means "use the default
    # (200) baked into the runtime form builder".
    max_chars = models.PositiveIntegerField(null=True, blank=True)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=300, blank=True)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_fielddefinition"
        verbose_name = "campo de tipo de solicitud"
        verbose_name_plural = "campos de tipo de solicitud"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "order"],
                name="unique_field_order_per_tipo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.label} [{self.field_type}]"
