"""URL routes for the plantilla_assets feature."""
from __future__ import annotations

from django.urls import path

from solicitudes.plantilla_assets.views.admin import (
    AssetDeleteView,
    AssetListJsonView,
    AssetListView,
    AssetUploadForPlantillaView,
    AssetUploadView,
)

app_name = "plantilla_assets"

urlpatterns = [
    path("", AssetListView.as_view(), name="list"),
    path("upload/", AssetUploadView.as_view(), name="upload_global"),
    path("list.json", AssetListJsonView.as_view(), name="list_json"),
    path(
        "plantilla/<uuid:plantilla_id>/upload/",
        AssetUploadForPlantillaView.as_view(),
        name="upload_plantilla",
    ),
    path("<uuid:asset_id>/delete/", AssetDeleteView.as_view(), name="delete"),
]
