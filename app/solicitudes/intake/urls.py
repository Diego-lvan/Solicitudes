"""URL routes for the intake feature (mounted under ``/solicitudes/``)."""
from __future__ import annotations

from django.urls import path

from solicitudes.intake.views.cancel import CancelOwnView
from solicitudes.intake.views.catalog import CatalogView
from solicitudes.intake.views.create import CreateSolicitudView
from solicitudes.intake.views.detail import SolicitudDetailView
from solicitudes.intake.views.mis_solicitudes import MisSolicitudesView

app_name = "intake"

urlpatterns = [
    path("", CatalogView.as_view(), name="catalog"),
    path("mis/", MisSolicitudesView.as_view(), name="mis_solicitudes"),
    path("crear/<slug:slug>/", CreateSolicitudView.as_view(), name="create"),
    path("<str:folio>/", SolicitudDetailView.as_view(), name="detail"),
    path("<str:folio>/cancelar/", CancelOwnView.as_view(), name="cancel"),
]
