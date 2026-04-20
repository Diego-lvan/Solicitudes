"""URL routes for the solicitudes app.

Future initiatives mount additional feature URL modules here:
- 004 — intake/, revision/, lifecycle/
- 005 — archivos/
- 006 — pdf/
"""
from __future__ import annotations

from django.urls import include, path

app_name = "solicitudes"

urlpatterns = [
    path("admin/tipos/", include(("solicitudes.tipos.urls", "tipos"))),
]
