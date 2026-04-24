"""Add ``User.gender`` — single-letter SIGA gender code.

Additive: legacy rows default to the empty string (``""`` = "not provided"),
so existing logins keep working unchanged. Reversible.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(blank=True, max_length=1),
        ),
    ]
