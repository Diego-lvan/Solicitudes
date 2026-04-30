"""Abstract :class:`MentorCsvImporter` — bulk import boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod

from mentores.schemas import CsvImportResult
from usuarios.schemas import UserDTO


class MentorCsvImporter(ABC):
    @abstractmethod
    def import_csv(self, content: bytes, *, actor: UserDTO) -> CsvImportResult:
        """Parse a CSV payload and upsert each row into the catalog.

        Expected format: a single column ``matricula`` with a header row.

        Per-row outcomes (counted in :class:`CsvImportResult`):
        - ``inserted`` — no prior row existed.
        - ``reactivated`` — an inactive row existed and was reactivated.
        - ``skipped_duplicates`` — an active row already existed; row ignored.
        - ``invalid_rows`` — format invalid; row skipped, error captured.

        Raises:
            CsvParseError: header missing, file unreadable, or no data rows
                were even attempted (so the upload itself is unusable).
        """
