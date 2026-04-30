"""Data migration: copy each ``Mentor`` row into a single ``MentorPeriodo``.

For every existing row in the legacy ``Mentor`` table, a one-period
``MentorPeriodo`` is inserted with the original ``fecha_alta`` carried
**verbatim** (not ``timezone.now()``). The new model deliberately omits
``auto_now_add`` so this carry-forward is not silently overwritten on insert.

``desactivado_por`` is left ``NULL`` for migrated rows because the legacy
schema did not capture the deactivator (per OQ-012-1).

Reverse is a no-op: rolling 0003 backwards would not restore the periods
opened after the cutover. ``0004_drop_mentor`` is forward-only for the same
reason — see its docstring.
"""
from __future__ import annotations

from django.db import migrations


def backfill(apps, schema_editor):
    Mentor = apps.get_model("mentores", "Mentor")
    MentorPeriodo = apps.get_model("mentores", "MentorPeriodo")
    to_create = [
        MentorPeriodo(
            matricula=m.matricula,
            fuente=m.fuente,
            nota=m.nota,
            fecha_alta=m.fecha_alta,
            fecha_baja=m.fecha_baja,
            creado_por_id=m.creado_por_id,
            desactivado_por_id=None,
        )
        for m in Mentor.objects.all()
    ]
    if to_create:
        MentorPeriodo.objects.bulk_create(to_create)


def noop_reverse(apps, schema_editor):
    """No-op. See module docstring."""


class Migration(migrations.Migration):

    dependencies = [
        ("mentores", "0002_mentor_periodo"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]
