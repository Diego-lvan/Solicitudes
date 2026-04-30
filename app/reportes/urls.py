"""URL routes for the reportes app."""
from __future__ import annotations

from django.urls import path

from reportes.views.dashboard import DashboardView
from reportes.views.export_csv import ExportCsvView
from reportes.views.export_pdf import ExportPdfView
from reportes.views.list import ReportListView

app_name = "reportes"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("lista/", ReportListView.as_view(), name="list"),
    path("exportar/csv/", ExportCsvView.as_view(), name="export_csv"),
    path("exportar/pdf/", ExportPdfView.as_view(), name="export_pdf"),
]
