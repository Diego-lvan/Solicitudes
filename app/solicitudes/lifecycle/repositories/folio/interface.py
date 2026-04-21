"""Folio sequence allocator interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class FolioRepository(ABC):
    """Persistence-backed sequence allocator for folios.

    The strategy is per-year monotonic: each call to ``allocate(year)`` returns
    the next integer for that year. Implementations must be safe under
    concurrent calls (row-level lock or DB sequence).
    """

    @abstractmethod
    def allocate(self, year: int) -> int:
        """Reserve and return the next sequence number for ``year``.

        Implementations must be atomic; two concurrent callers must never
        receive the same number.
        """
