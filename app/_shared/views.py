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


# Per-role landing pages. Roles without a real "home" yet (alumno/docente
# solicitud lists arrive in 004; staff review queue arrives in 004) bounce to
# the profile page so the user sees something sensible instead of a 404.
_HOME_FOR_ROLE: dict[str, str] = {
    Role.ADMIN.value: "/solicitudes/admin/tipos/",
}
_DEFAULT_AUTHED_HOME = "/auth/me"


def home(request: HttpRequest) -> HttpResponse:
    """Role-aware landing page for the project root.

    Anonymous → bounce to the auth provider login. Authenticated → role-specific
    home (admins land on the catalog; everyone else lands on their profile
    until their feature ships).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return HttpResponseRedirect(settings.LOGIN_URL)

    role = getattr(user, "role", "")
    target = _HOME_FOR_ROLE.get(role, _DEFAULT_AUTHED_HOME)
    return redirect(target)
