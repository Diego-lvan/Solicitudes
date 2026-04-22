"""URL routes for the solicitudes app.

Future initiatives mount additional feature URL modules here:
- 005 — archivos/
"""
from __future__ import annotations

from django.urls import include, path, re_path

from solicitudes.pdf.views.download import RenderSolicitudPdfView

app_name = "solicitudes"

urlpatterns = [
    path("admin/tipos/", include(("solicitudes.tipos.urls", "tipos"))),
    path(
        "admin/plantillas/",
        include(("solicitudes.pdf.urls", "plantillas")),
    ),
    path("revision/", include(("solicitudes.revision.urls", "revision"))),
    # PDF download lives at "<folio>/pdf/" sharing the folio prefix used by
    # intake detail. Constrained to the actual folio shape (SOL-YYYY-NNNNN)
    # so a literal "/pdf/" cannot collide with the intake detail catch-all.
    re_path(
        r"^(?P<folio>[A-Z]+-\d{4}-\d{4,})/pdf/$",
        RenderSolicitudPdfView.as_view(),
        name="pdf_download",
    ),
    # Intake routes ("", "mis/", "crear/<slug>/", "<folio>/") are mounted last
    # so the more specific prefixes above match first.
    path("", include(("solicitudes.intake.urls", "intake"))),
]
