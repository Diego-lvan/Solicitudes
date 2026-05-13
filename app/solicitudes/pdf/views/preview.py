"""Admin-only sample-PDF preview for a plantilla.

Renders the plantilla against synthetic context so the admin can iterate on
layout without creating a real solicitud first.
"""
from __future__ import annotations

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin

from solicitudes.pdf.dependencies import get_pdf_service
from usuarios.permissions import AdminRequiredMixin


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PlantillaPreviewView(AdminRequiredMixin, View):
    """``GET /admin/plantillas/<id>/preview.pdf``.

    The plantilla detail page embeds this URL in an ``<iframe>``. Django's
    default ``X-Frame-Options: DENY`` would silently blank the frame, so we
    relax to ``SAMEORIGIN`` for this view only.
    """

    def get(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        result = get_pdf_service().render_sample(plantilla_id)
        # Inline so the iframe in detail.html displays the PDF in-browser.
        response = HttpResponse(result.bytes_, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="{result.suggested_filename}"'
        )
        return response
