"""Add ArchivoSolicitud — index row for files attached to solicitudes."""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solicitudes", "0003_remove_tiposolicitud_plantilla_id_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchivoSolicitud",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("field_id", models.UUIDField(blank=True, null=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("FORM", "Archivo de formulario"),
                            ("COMPROBANTE", "Comprobante de pago"),
                        ],
                        max_length=16,
                    ),
                ),
                ("original_filename", models.CharField(max_length=255)),
                ("stored_path", models.CharField(max_length=500)),
                ("content_type", models.CharField(max_length=100)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "solicitud",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="archivos",
                        to="solicitudes.solicitud",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "archivo de solicitud",
                "verbose_name_plural": "archivos de solicitud",
                "db_table": "solicitudes_archivosolicitud",
                "indexes": [
                    models.Index(
                        fields=["solicitud", "kind"],
                        name="solicitudes_solicit_a7b7c3_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("kind", "FORM")),
                        fields=("solicitud", "field_id"),
                        name="archivo_unique_per_field",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("kind", "COMPROBANTE")),
                        fields=("solicitud",),
                        name="archivo_unique_comprobante",
                    ),
                ],
            },
        ),
    ]
