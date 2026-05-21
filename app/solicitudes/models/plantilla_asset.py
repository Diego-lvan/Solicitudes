"""PlantillaAsset — image uploaded by admin to embed in PDF plantillas.

Two scopes: ``global`` (institutional assets like the UAZ logo, available to
every plantilla) and ``plantilla`` (specific to a single plantilla).

Plantillas reference an asset by slug via ``{{ assets.<slug> }}``; the pdf
service resolves the slug to a ``data:`` URI at render time so the bytes are
embedded in the PDF (preserving determinism across deployments).
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class PlantillaAsset(models.Model):
    SCOPE_GLOBAL = "global"
    SCOPE_PLANTILLA = "plantilla"
    SCOPE_CHOICES = (
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_PLANTILLA, "Por plantilla"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64)
    nombre = models.CharField(max_length=120)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    plantilla = models.ForeignKey(
        "solicitudes.PlantillaSolicitud",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assets",
    )
    imagen = models.FileField(upload_to="plantilla_assets/%Y/%m/")
    mime_type = models.CharField(max_length=50)
    size_bytes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_plantillaasset"
        verbose_name = "asset de plantilla"
        verbose_name_plural = "assets de plantillas"
        ordering = ["scope", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(scope="global"),
                name="unique_global_asset_slug",
            ),
            models.UniqueConstraint(
                fields=["plantilla", "slug"],
                condition=models.Q(scope="plantilla"),
                name="unique_plantilla_asset_slug",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(scope="global", plantilla__isnull=True)
                    | models.Q(scope="plantilla", plantilla__isnull=False)
                ),
                name="plantilla_asset_scope_consistency",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.scope})"
