"""Project URL root."""
from __future__ import annotations

from django.conf import settings
from django.urls import include, path, re_path

from _shared.views import health, home, serve_media

_media_prefix = settings.MEDIA_URL.lstrip("/")

urlpatterns = [
    path("health/", health, name="health"),
    path("", home, name="home"),
    path("", include(("usuarios.urls", "usuarios"))),
    path("solicitudes/", include(("solicitudes.urls", "solicitudes"))),
    path("mentores/", include(("mentores.urls", "mentores"))),
    path("reportes/", include(("reportes.urls", "reportes"))),
    # App-served uploads for proxy-less deploys (Railway demo). Behind nginx the
    # /media/ location short-circuits this before it reaches Django.
    re_path(rf"^{_media_prefix}(?P<path>.*)$", serve_media, name="media"),
]
