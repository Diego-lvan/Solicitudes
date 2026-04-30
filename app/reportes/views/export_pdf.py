"""PDF export view — streams the filtered summary as application/pdf."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views import View

from reportes.dependencies import get_pdf_exporter, get_report_service
from reportes.permissions import AdminRequiredMixin
from reportes.views._helpers import get_filter_from_request


class ExportPdfView(AdminRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        filter = get_filter_from_request(request)
        # PDF goes through dashboard() and list_paginated() — share one service.
        exporter = get_pdf_exporter(report_service=get_report_service())
        body = exporter.export(filter=filter)
        response = HttpResponse(body, content_type=exporter.content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="{exporter.filename}"'
        )
        return response
