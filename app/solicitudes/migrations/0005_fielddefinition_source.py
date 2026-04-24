"""Add FieldDefinition.source — auto-fill source for dynamic-form fields.

Additive: legacy rows default to ``USER_INPUT`` so the existing catalog keeps
working unchanged. Reversible (the column can be dropped).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solicitudes", "0004_archivosolicitud"),
    ]

    operations = [
        migrations.AddField(
            model_name="fielddefinition",
            name="source",
            field=models.CharField(
                choices=[
                    ("USER_INPUT", "El solicitante lo escribe"),
                    ("USER_FULL_NAME", "Auto · Nombre completo"),
                    ("USER_PROGRAMA", "Auto · Programa"),
                    ("USER_EMAIL", "Auto · Correo"),
                    ("USER_MATRICULA", "Auto · Matrícula"),
                    ("USER_SEMESTRE", "Auto · Semestre"),
                ],
                default="USER_INPUT",
                max_length=24,
            ),
        ),
    ]
