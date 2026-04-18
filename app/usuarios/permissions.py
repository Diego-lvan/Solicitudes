"""Role-based view mixins.

Mixins raise :class:`AppError` subclasses; ``AppErrorMiddleware`` turns
``AuthenticationRequired`` into a redirect to the provider login and
``Unauthorized`` into a 403 page.
"""
from __future__ import annotations

from typing import Any, ClassVar

from django.http import HttpRequest, HttpResponse

from _shared.exceptions import AuthenticationRequired, Unauthorized
from usuarios.constants import Role


class LoginRequiredMixin:
    """Aborts the request with ``AuthenticationRequired`` for anonymous users."""

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            raise AuthenticationRequired("Inicia sesión para continuar.")
        response: HttpResponse = super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
        return response


class RoleRequiredMixin(LoginRequiredMixin):
    """Allows only users whose role is in ``required_roles``."""

    required_roles: ClassVar[frozenset[Role]] = frozenset()

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            raise AuthenticationRequired("Inicia sesión para continuar.")
        user_role = getattr(request.user, "role", None)
        if user_role not in {r.value for r in self.required_roles}:
            raise Unauthorized("Tu rol no tiene acceso a esta sección.")
        response: HttpResponse = super().dispatch(request, *args, **kwargs)
        return response


class AlumnoRequiredMixin(RoleRequiredMixin):
    required_roles: ClassVar[frozenset[Role]] = frozenset({Role.ALUMNO})


class DocenteRequiredMixin(RoleRequiredMixin):
    required_roles: ClassVar[frozenset[Role]] = frozenset({Role.DOCENTE})


class PersonalRequiredMixin(RoleRequiredMixin):
    required_roles: ClassVar[frozenset[Role]] = frozenset(
        {Role.CONTROL_ESCOLAR, Role.RESPONSABLE_PROGRAMA}
    )


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles: ClassVar[frozenset[Role]] = frozenset({Role.ADMIN})
