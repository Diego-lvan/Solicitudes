"""URL routes for the usuarios app."""
from __future__ import annotations

from django.conf import settings
from django.urls import include, path

from usuarios.views.callback import CallbackView
from usuarios.views.logout import LogoutView
from usuarios.views.me import MeView

app_name = "usuarios"

urlpatterns = [
    path("auth/callback", CallbackView.as_view(), name="callback"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/me", MeView.as_view(), name="me"),
    path("usuarios/", include("usuarios.directory.urls")),
]

# Dev-only URL: stand-in for the external auth provider while OQ-002-1 is open.
# The route is mounted ONLY when DEBUG=True so it cannot be reached in
# production. Initiative 010 will remove this view entirely.
if settings.DEBUG:
    from usuarios.views.dev_login import DevLoginView

    urlpatterns.append(path("auth/dev-login", DevLoginView.as_view(), name="dev_login"))
