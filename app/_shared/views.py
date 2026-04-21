"""Cross-cutting views used by the project root URL conf."""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect

from usuarios.constants import Role


def health(request: HttpRequest) -> JsonResponse:
    """Liveness probe — returns 200 with the request id from middleware."""
    return JsonResponse(
        {"status": "ok", "request_id": getattr(request, "request_id", None)}
    )


# Per-role landing pages. Creators land on the intake catalog so they can file
# a new solicitud in one click; personal lands on the revision queue; admins
# keep the tipos catalog as home since they typically curate the catalog
# before anything else.
_HOME_FOR_ROLE: dict[str, str] = {
    Role.ADMIN.value: "/solicitudes/admin/tipos/",
    Role.ALUMNO.value: "/solicitudes/",
    Role.DOCENTE.value: "/solicitudes/",
    Role.CONTROL_ESCOLAR.value: "/solicitudes/revision/",
    Role.RESPONSABLE_PROGRAMA.value: "/solicitudes/revision/",
}
_DEFAULT_AUTHED_HOME = "/auth/me"


def home(request: HttpRequest) -> HttpResponse:
    """Role-aware landing page for the project root.

    Anonymous → bounce to the auth provider login. Authenticated → role-specific
    home: alumnos/docentes land on the intake catalog, control-escolar /
    responsable-programa land on the revision queue, admins land on the tipos
    catalog. Roles without a mapped home fall back to the profile page.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return HttpResponseRedirect(settings.LOGIN_URL)

    role = getattr(user, "role", "")
    target = _HOME_FOR_ROLE.get(role, _DEFAULT_AUTHED_HOME)
    return redirect(target)
