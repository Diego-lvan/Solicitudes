"""PDF exporter — renders dashboard summary + (capped) row table via WeasyPrint."""
from __future__ import annotations

from django.template.loader import render_to_string

from _shared.pdf import render_pdf
from reportes.schemas import ReportFilter
from reportes.services.export_service.interface import ExportService
from reportes.services.report_service.interface import ReportService

# Cap chosen so a single PDF render finishes in seconds on dev hardware
# (RNF-05: < 5s for 1000 rows). Above this we omit the row table and tell the
# user to use the CSV export.
_PDF_ROW_CAP = 1000


class PdfExportImpl(ExportService):
    def __init__(self, *, report_service: ReportService) -> None:
        self._reports = report_service

    @property
    def content_type(self) -> str:
        return "application/pdf"

    @property
    def filename(self) -> str:
        return "solicitudes.pdf"

    def export(self, *, filter: ReportFilter) -> bytes:
        dashboard = self._reports.dashboard(filter=filter)

        # Stream up to one row past the cap so we detect overflow without
        # materializing the entire result set when the filter happens to match
        # millions. A single source of truth for the truncation flag — no
        # second comparison against `dashboard.total` (which could disagree
        # with the iterator under concurrent writes).
        rows: list = []
        truncated = False
        for row in self._reports.iter_for_admin(filter=filter):
            if len(rows) >= _PDF_ROW_CAP:
                truncated = True
                break
            rows.append(row)

        html = render_to_string(
            "reportes/export_pdf.html",
            {
                "dashboard": dashboard,
                "rows": [] if truncated else rows,
                "truncated": truncated,
                "row_cap": _PDF_ROW_CAP,
            },
        )
        return render_pdf(html)
