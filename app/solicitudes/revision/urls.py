"""URL routes for the revision feature (mounted under ``/revision/``)."""
from __future__ import annotations

from django.urls import path

from solicitudes.revision.views.cancel import CancelByPersonalView
from solicitudes.revision.views.detail import RevisionDetailView
from solicitudes.revision.views.finalize import FinalizeView
from solicitudes.revision.views.queue import QueueView
from solicitudes.revision.views.take import TakeView

app_name = "revision"

urlpatterns = [
    path("", QueueView.as_view(), name="queue"),
    path("<str:folio>/", RevisionDetailView.as_view(), name="detail"),
    path("<str:folio>/atender/", TakeView.as_view(), name="take"),
    path("<str:folio>/finalizar/", FinalizeView.as_view(), name="finalize"),
    path("<str:folio>/cancelar/", CancelByPersonalView.as_view(), name="cancel"),
]
