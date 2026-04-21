"""Default folio service — formats the repository's allocated sequence."""
from __future__ import annotations

from solicitudes.lifecycle.repositories.folio.interface import FolioRepository
from solicitudes.lifecycle.services.folio_service.interface import FolioService


class DefaultFolioService(FolioService):
    """Delegates allocation to ``FolioRepository`` and formats the folio string."""

    def __init__(self, folio_repository: FolioRepository) -> None:
        self._repo = folio_repository

    def next_folio(self, *, year: int) -> str:
        n = self._repo.allocate(year)
        return f"SOL-{year}-{n:05d}"
