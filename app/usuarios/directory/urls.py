"""URL routes for the admin user directory feature."""
from __future__ import annotations

from django.urls import path

from usuarios.directory.views.detail import DirectoryDetailView
from usuarios.directory.views.list import DirectoryListView

app_name = "directory"

urlpatterns = [
    path("", DirectoryListView.as_view(), name="list"),
    path("<str:matricula>/", DirectoryDetailView.as_view(), name="detail"),
]
