"""URL routes for archivos (mounted under ``/solicitudes/archivos/``)."""
from __future__ import annotations

from django.urls import path

from solicitudes.archivos.views.download import DownloadArchivoView

app_name = "archivos"

urlpatterns = [
    path("<uuid:archivo_id>/", DownloadArchivoView.as_view(), name="download"),
]
