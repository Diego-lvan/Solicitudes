"""Helpers for extracting the typed actor (UserDTO) from a request.

The ``JwtAuthenticationMiddleware`` attaches ``request.user_dto: UserDTO`` on
every authenticated request. Views guarded by ``LoginRequiredMixin`` (or any
subclass) can rely on it being present. This helper centralises the access
pattern so individual views don't need ``# type: ignore`` or ``getattr`` dances.
"""
from __future__ import annotations

from django.http import HttpRequest

from _shared.exceptions import AuthenticationRequired
from usuarios.schemas import UserDTO


def actor_from_request(request: HttpRequest) -> UserDTO:
    """Return the typed actor for an authenticated request.

    Must only be called from views protected by ``LoginRequiredMixin``. If
    ``request.user_dto`` is missing — which means an anonymous request slipped
    past the login mixin — raise :class:`AuthenticationRequired` so the global
    error handler issues the same redirect the mixin would.
    """
    actor: UserDTO | None = getattr(request, "user_dto", None)
    if actor is None:
        raise AuthenticationRequired("Inicia sesión para continuar.")
    return actor
