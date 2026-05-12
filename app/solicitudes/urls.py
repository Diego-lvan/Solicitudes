"""URL routes for the solicitudes app.

Future initiatives mount additional feature URL modules here:
- 005 — archivos/
- 006 — pdf/
"""
from __future__ import annotations

from django.urls import include, path

app_name = "solicitudes"

urlpatterns = [
    path("admin/tipos/", include(("solicitudes.tipos.urls", "tipos"))),
    path("revision/", include(("solicitudes.revision.urls", "revision"))),
    # Intake routes ("", "mis/", "crear/<slug>/", "<folio>/") are mounted last
    # so the more specific prefixes above match first.
    path("", include(("solicitudes.intake.urls", "intake"))),
]
