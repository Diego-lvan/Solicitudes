"""CSV exporter — streams the filtered admin list with UTF-8 BOM."""
from __future__ import annotations

import csv
import io

from reportes.schemas import ReportFilter
from reportes.services.export_service.interface import ExportService
from reportes.services.report_service.interface import ReportService

# Larger than the HTTP `PageRequest` cap (100): the CSV path streams via the
# DB-side iterator and never crosses the HTTP boundary, so we use 500 to keep
# round-trip overhead low for large exports.
_CHUNK_SIZE = 500
_HEADER = [
    "folio",
    "tipo",
    "solicitante_matricula",
    "solicitante_nombre",
    "estado",
    "requiere_pago",
    "pago_exento",
    "created_at",
    "updated_at",
]


class CsvExportImpl(ExportService):
    """Materializes filtered solicitudes into UTF-8-BOM CSV bytes.

    Streams via ``ReportService.iter_for_admin`` so the only DB round trip is
    the cursor walk — no per-chunk ``COUNT(*)``.
    """

    def __init__(self, *, report_service: ReportService) -> None:
        self._reports = report_service

    @property
    def content_type(self) -> str:
        return "text/csv; charset=utf-8"

    @property
    def filename(self) -> str:
        return "solicitudes.csv"

    def export(self, *, filter: ReportFilter) -> bytes:
        buffer = io.StringIO()
        # \r\n is the line terminator Excel / Office expect for CSV on every
        # platform; LF-only is mishandled by older Excel versions.
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(_HEADER)
        for row in self._reports.iter_for_admin(
            filter=filter, chunk_size=_CHUNK_SIZE
        ):
            writer.writerow(
                [
                    row.folio,
                    row.tipo_nombre,
                    row.solicitante_matricula,
                    row.solicitante_nombre,
                    row.estado.value,
                    "1" if row.requiere_pago else "0",
                    "1" if row.pago_exento else "0",
                    row.created_at.isoformat(),
                    row.updated_at.isoformat(),
                ]
            )
        # Excel needs a UTF-8 BOM to recognize the encoding of accented text.
        return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
