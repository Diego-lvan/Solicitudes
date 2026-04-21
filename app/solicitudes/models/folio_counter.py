"""FolioCounter — per-year sequence allocator for solicitud folios.

The folio shape is ``SOL-YYYY-NNNNN``. We allocate ``NNNNN`` by locking the
counter row (``SELECT … FOR UPDATE``) and incrementing ``last``. This is the
portable strategy across Postgres and SQLite (used in dev). Throughput is
bounded by row-level lock contention, which is fine for our load profile.
"""
from __future__ import annotations

from django.db import models


class FolioCounter(models.Model):
    year = models.PositiveIntegerField(primary_key=True)
    last = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "solicitudes"
        db_table = "solicitudes_foliocounter"
        verbose_name = "contador de folio"
        verbose_name_plural = "contadores de folio"

    def __str__(self) -> str:
        return f"{self.year}: {self.last}"
