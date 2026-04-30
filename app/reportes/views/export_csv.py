"""CSV export view — streams the filtered list as text/csv with UTF-8 BOM."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views import View

from reportes.dependencies import get_csv_exporter, get_report_service
from reportes.permissions import AdminRequiredMixin
from reportes.views._helpers import get_filter_from_request


class ExportCsvView(AdminRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        filter = get_filter_from_request(request)
        # Build the report service once and share it; the exporter calls
        # `list_paginated` repeatedly and we want a single composed graph.
        exporter = get_csv_exporter(report_service=get_report_service())
        body = exporter.export(filter=filter)
        response = HttpResponse(body, content_type=exporter.content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="{exporter.filename}"'
        )
        return response
