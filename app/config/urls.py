"""Project URL root."""
from __future__ import annotations

from django.urls import include, path
from django.views.generic import RedirectView

from _shared.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", RedirectView.as_view(url="/solicitudes/", permanent=False)),
    path("", include(("usuarios.urls", "usuarios"))),
    # Filled by later initiatives:
    # path("solicitudes/", include(("solicitudes.urls", "solicitudes"))),
    # path("mentores/", include(("mentores.urls", "mentores"))),
    # path("reportes/", include(("reportes.urls", "reportes"))),
]
