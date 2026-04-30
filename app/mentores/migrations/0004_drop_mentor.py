"""Drop the legacy ``Mentor`` table.

**Forward-only.** ``0003_backfill_mentor_periodos`` has already copied every
legacy row into ``MentorPeriodo``. Rolling this migration back re-creates an
empty ``Mentor`` table for migration-graph completeness, but the row data is
gone — rolling all the way back to ``0001`` destroys history. The reverse
path exists only so ``manage.py migrate mentores 0001`` does not blow up
mid-run; it is **not** a recovery mechanism.

If you need to roll back the historicization, restore the ``mentores_mentor``
table from a backup taken before ``0002`` ran.
"""
from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mentores", "0003_backfill_mentor_periodos"),
    ]

    operations = [
        migrations.DeleteModel(name="Mentor"),
    ]
