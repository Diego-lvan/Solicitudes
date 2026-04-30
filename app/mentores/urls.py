"""URL routes for the mentores app."""
from __future__ import annotations

from django.urls import path

from mentores.views.add import AddMentorView
from mentores.views.bulk_deactivate import BulkDeactivateMentorsView
from mentores.views.deactivate import DeactivateMentorView
from mentores.views.detail import MentorDetailView
from mentores.views.import_csv import ImportCsvView
from mentores.views.list import MentorListView

app_name = "mentores"

urlpatterns = [
    path("", MentorListView.as_view(), name="list"),
    path("agregar/", AddMentorView.as_view(), name="add"),
    path("importar/", ImportCsvView.as_view(), name="import_csv"),
    path(
        "desactivar-bulk/",
        BulkDeactivateMentorsView.as_view(),
        name="deactivate_bulk",
    ),
    path(
        "<str:matricula>/desactivar/",
        DeactivateMentorView.as_view(),
        name="deactivate",
    ),
    path("<str:matricula>/", MentorDetailView.as_view(), name="detail"),
]
