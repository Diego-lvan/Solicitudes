"""HTTP view that streams a freshly-rendered solicitud PDF."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views import View

from solicitudes.pdf.dependencies import get_pdf_service
from usuarios.permissions import LoginRequiredMixin


class RenderSolicitudPdfView(LoginRequiredMixin, View):
    """``GET /solicitudes/<folio>/pdf/`` — render and stream the PDF.

    Authorisation lives in :class:`PdfService` (so it stays one place across
    HTML and any future API surface). The view only translates the result.
    """

    def get(self, request: HttpRequest, folio: str) -> HttpResponse:
        service = get_pdf_service()
        result = service.render_for_solicitud(folio, request.user_dto)  # type: ignore[attr-defined]
        response = HttpResponse(result.bytes_, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{result.suggested_filename}"'
        )
        return response
