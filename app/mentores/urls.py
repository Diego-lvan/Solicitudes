"""URL routes for the mentores app."""
from __future__ import annotations

from django.urls import path

from mentores.views.add import AddMentorView
from mentores.views.deactivate import DeactivateMentorView
from mentores.views.import_csv import ImportCsvView
from mentores.views.list import MentorListView

app_name = "mentores"

urlpatterns = [
    path("", MentorListView.as_view(), name="list"),
    path("agregar/", AddMentorView.as_view(), name="add"),
    path("importar/", ImportCsvView.as_view(), name="import_csv"),
    path(
        "<str:matricula>/desactivar/",
        DeactivateMentorView.as_view(),
        name="deactivate",
    ),
]
