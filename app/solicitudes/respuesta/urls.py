"""URL routes for the respuesta feature."""
from __future__ import annotations

from django.urls import path

from solicitudes.respuesta.views.personal import CreateRespuestaView
from solicitudes.respuesta.views.shared import DownloadArchivoRespuestaView

app_name = "respuesta"

urlpatterns = [
    path(
        "<str:folio>/respuestas/nueva/",
        CreateRespuestaView.as_view(),
        name="create",
    ),
    path(
        "<str:folio>/respuestas/<uuid:respuesta_id>/archivos/<uuid:archivo_id>/",
        DownloadArchivoRespuestaView.as_view(),
        name="download",
    ),
]
