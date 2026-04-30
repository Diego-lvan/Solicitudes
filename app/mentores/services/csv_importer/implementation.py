"""Default :class:`MentorCsvImporter` — partial-success row counting."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from django.db import transaction

from mentores.constants import MentorSource
from mentores.exceptions import CsvParseError
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import CsvImportResult, MentorUpsertInput
from mentores.services.csv_importer.interface import MentorCsvImporter
from mentores.validators import is_valid_matricula, matricula_format_message
from usuarios.schemas import UserDTO

EXPECTED_HEADER = "matricula"


class DefaultMentorCsvImporter(MentorCsvImporter):
    """Reads a CSV byte payload, validates each row, delegates writes to the repo."""

    def __init__(
        self,
        *,
        mentor_repository: MentorRepository,
        logger: logging.Logger,
    ) -> None:
        self._repo = mentor_repository
        self._logger = logger

    def import_csv(self, content: bytes, *, actor: UserDTO) -> CsvImportResult:
        text = self._decode(content)
        reader = csv.reader(io.StringIO(text))
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvParseError(
                "El archivo está vacío.",
                field_errors={"file": ["El archivo está vacío."]},
            ) from exc
        self._assert_header(header)

        total_rows = 0
        inserted = 0
        reactivated = 0
        skipped = 0
        invalid: list[dict[str, Any]] = []

        # ``atomic()`` guarantees that an unexpected DB error mid-import
        # rolls back the entire batch. Row-level validation failures DO NOT
        # abort — they accumulate in ``invalid_rows`` (partial success per spec).
        with transaction.atomic():
            for row_index, row in enumerate(reader, start=2):  # +1 header, +1 1-based
                total_rows += 1
                raw = (row[0] if row else "").strip()
                if not raw:
                    invalid.append(
                        {"row": row_index, "matricula": "", "error": "Fila vacía."}
                    )
                    continue
                if not is_valid_matricula(raw):
                    invalid.append(
                        {
                            "row": row_index,
                            "matricula": raw,
                            "error": matricula_format_message(),
                        }
                    )
                    continue
                _, outcome = self._repo.upsert(
                    MentorUpsertInput(
                        matricula=raw,
                        fuente=MentorSource.CSV,
                        nota="",
                        creado_por_matricula=actor.matricula,
                    )
                )
                if outcome is UpsertOutcome.INSERTED:
                    inserted += 1
                elif outcome is UpsertOutcome.REACTIVATED:
                    reactivated += 1
                else:
                    skipped += 1

        self._logger.info(
            "mentor.csv_import actor=%s total=%d inserted=%d reactivated=%d "
            "skipped=%d invalid=%d",
            actor.matricula,
            total_rows,
            inserted,
            reactivated,
            skipped,
            len(invalid),
        )
        return CsvImportResult(
            total_rows=total_rows,
            inserted=inserted,
            reactivated=reactivated,
            skipped_duplicates=skipped,
            invalid_rows=invalid,
        )

    @staticmethod
    def _decode(content: bytes) -> str:
        # Strip a UTF-8 BOM if present; admins frequently export from Excel
        # which prepends one.
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CsvParseError(
                "El archivo no es UTF-8 válido.",
                field_errors={"file": ["El archivo no es UTF-8 válido."]},
            ) from exc

    @staticmethod
    def _assert_header(row: list[str]) -> None:
        if not row or row[0].strip().lower() != EXPECTED_HEADER:
            raise CsvParseError(
                "El encabezado debe ser 'matricula'.",
                field_errors={
                    "file": ["La primera fila debe contener el encabezado 'matricula'."]
                },
            )
