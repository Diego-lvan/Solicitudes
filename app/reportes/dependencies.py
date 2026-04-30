"""DI factory functions for the reportes feature."""
from __future__ import annotations

from reportes.services.export_service.csv_implementation import CsvExportImpl
from reportes.services.export_service.interface import ExportService
from reportes.services.export_service.pdf_implementation import PdfExportImpl
from reportes.services.report_service.implementation import DefaultReportService
from reportes.services.report_service.interface import ReportService
from solicitudes.lifecycle.dependencies import get_lifecycle_service


def get_report_service() -> ReportService:
    return DefaultReportService(lifecycle_service=get_lifecycle_service())


def get_csv_exporter(*, report_service: ReportService | None = None) -> ExportService:
    return CsvExportImpl(report_service=report_service or get_report_service())


def get_pdf_exporter(*, report_service: ReportService | None = None) -> ExportService:
    return PdfExportImpl(report_service=report_service or get_report_service())
