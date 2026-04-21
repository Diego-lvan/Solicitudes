"""ORM-backed folio allocator using ``SELECT ... FOR UPDATE`` on FolioCounter."""
from __future__ import annotations

from django.db import transaction

from solicitudes.lifecycle.repositories.folio.interface import FolioRepository
from solicitudes.models import FolioCounter


class OrmFolioRepository(FolioRepository):
    """Counter-row strategy. Portable across Postgres and SQLite (dev).

    Each ``allocate(year)`` call:
    1. Locks the counter row for ``year`` (creating it if needed).
    2. Increments ``last`` and saves.
    3. Returns the new value.

    The whole sequence runs inside an atomic block so a crash in step 2 leaves
    the counter unchanged.
    """

    def allocate(self, year: int) -> int:
        with transaction.atomic():
            counter, _ = FolioCounter.objects.select_for_update().get_or_create(
                year=year, defaults={"last": 0}
            )
            counter.last += 1
            counter.save(update_fields=["last"])
            return counter.last
