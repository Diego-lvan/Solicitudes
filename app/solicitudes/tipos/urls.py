"""URL routes for the tipos admin feature."""
from __future__ import annotations

from django.urls import path

from solicitudes.tipos.views.create import TipoCreateView
from solicitudes.tipos.views.delete import TipoDeactivateView
from solicitudes.tipos.views.detail import TipoDetailView
from solicitudes.tipos.views.edit import TipoEditView
from solicitudes.tipos.views.list import TipoListView

app_name = "tipos"

urlpatterns = [
    path("", TipoListView.as_view(), name="list"),
    path("nuevo/", TipoCreateView.as_view(), name="create"),
    path("<uuid:tipo_id>/", TipoDetailView.as_view(), name="detail"),
    path("<uuid:tipo_id>/editar/", TipoEditView.as_view(), name="edit"),
    path(
        "<uuid:tipo_id>/desactivar/",
        TipoDeactivateView.as_view(),
        name="deactivate",
    ),
]
