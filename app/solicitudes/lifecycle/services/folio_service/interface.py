"""Folio service — formats the next per-year sequence into ``SOL-YYYY-NNNNN``."""
from __future__ import annotations

from abc import ABC, abstractmethod


class FolioService(ABC):
    @abstractmethod
    def next_folio(self, *, year: int) -> str:
        """Return the next folio for ``year`` in canonical ``SOL-YYYY-NNNNN`` form."""
