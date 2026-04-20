"""Project URL root."""
from __future__ import annotations

from django.urls import include, path

from _shared.views import health, home

urlpatterns = [
    path("health/", health, name="health"),
    path("", home, name="home"),
    path("", include(("usuarios.urls", "usuarios"))),
    path("solicitudes/", include(("solicitudes.urls", "solicitudes"))),
    # Filled by later initiatives:
    # path("mentores/", include(("mentores.urls", "mentores"))),
    # path("reportes/", include(("reportes.urls", "reportes"))),
]
