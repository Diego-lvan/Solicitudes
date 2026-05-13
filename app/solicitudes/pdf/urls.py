"""URL routes for the pdf feature (admin plantilla CRUD + per-solicitud download)."""
from __future__ import annotations

from django.urls import path

from solicitudes.pdf.views.create import PlantillaCreateView
from solicitudes.pdf.views.delete import PlantillaDeactivateView
from solicitudes.pdf.views.detail import PlantillaDetailView
from solicitudes.pdf.views.edit import PlantillaEditView
from solicitudes.pdf.views.list import PlantillaListView
from solicitudes.pdf.views.preview import PlantillaPreviewView

app_name = "plantillas"

urlpatterns = [
    path("", PlantillaListView.as_view(), name="list"),
    path("nueva/", PlantillaCreateView.as_view(), name="create"),
    path("<uuid:plantilla_id>/", PlantillaDetailView.as_view(), name="detail"),
    path(
        "<uuid:plantilla_id>/preview.pdf",
        PlantillaPreviewView.as_view(),
        name="preview",
    ),
    path("<uuid:plantilla_id>/editar/", PlantillaEditView.as_view(), name="edit"),
    path(
        "<uuid:plantilla_id>/desactivar/",
        PlantillaDeactivateView.as_view(),
        name="deactivate",
    ),
]
