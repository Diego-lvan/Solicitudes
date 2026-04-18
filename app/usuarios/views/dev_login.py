"""``GET/POST /auth/dev-login`` — development-only login picker.

This view exists as a stand-in for the real external auth provider (OQ-002-1).
It mints a JWT server-side and bounces through ``/auth/callback`` so the entire
production code path is exercised — only the *source* of the token is fake.

The route is **only mounted when ``settings.DEBUG=True``** (URL-level gate, so
the URL literally does not exist in production). A leaked dev JWT could only
be replayed against a production deployment if it shared the same
``JWT_SECRET``, which the prod settings forbid via ``_required("JWT_SECRET")``.

Initiative 010 will remove this view and wire the real provider in its place.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import jwt
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from usuarios.constants import PROVIDER_ROLE_MAP, Role
from usuarios.dependencies import get_user_repository
from usuarios.exceptions import UserNotFound
from usuarios.schemas import CreateOrUpdateUserInput

# Reverse map: internal Role → first provider role string that maps to it.
_ROLE_TO_PROVIDER_CLAIM: dict[Role, str] = {
    role: claim for claim, role in PROVIDER_ROLE_MAP.items()
}

# Quickstart preset matriculas, one per role.
_QUICKSTART_USERS: list[tuple[Role, str, str]] = [
    (Role.ALUMNO, "ALUMNO_TEST", "alumno.test@uaz.edu.mx"),
    (Role.DOCENTE, "DOCENTE_TEST", "docente.test@uaz.edu.mx"),
    (Role.CONTROL_ESCOLAR, "CE_TEST", "ce.test@uaz.edu.mx"),
    (Role.RESPONSABLE_PROGRAMA, "RP_TEST", "rp.test@uaz.edu.mx"),
    (Role.ADMIN, "ADMIN_TEST", "admin.test@uaz.edu.mx"),
]


class DevLoginView(View):
    """Lists existing users + 5 role-quickstart buttons; mints a real JWT on click."""

    # Django's `View` declares this as an instance attribute, so we cannot
    # narrow to ClassVar without provoking mypy. Ruff's RUF012 doesn't apply
    # here — the framework owns the contract.
    http_method_names = ["get", "post"]  # noqa: RUF012

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        existing = get_user_repository().list_all()
        return render(
            request,
            "usuarios/dev_login.html",
            {
                "existing_users": existing,
                "quickstart": [
                    {"role": role.value, "matricula": matricula, "email": email}
                    for role, matricula, email in _QUICKSTART_USERS
                ],
            },
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        action = request.POST.get("action", "")
        repo = get_user_repository()

        if action == "quickstart":
            role_value = request.POST.get("role", "")
            try:
                role = Role(role_value)
            except ValueError:
                return _bad_request("rol inválido")
            preset = next((p for p in _QUICKSTART_USERS if p[0] is role), None)
            if preset is None:
                return _bad_request("rol no preconfigurado")
            _, matricula, email = preset
            repo.upsert(
                CreateOrUpdateUserInput(matricula=matricula, email=email, role=role)
            )
        elif action == "login":
            matricula = request.POST.get("matricula", "").strip()
            if not matricula:
                return _bad_request("matrícula requerida")
            try:
                dto = repo.get_by_matricula(matricula)
            except UserNotFound:
                return _bad_request("usuario no encontrado")
            role = dto.role
            email = dto.email
        else:
            return _bad_request("acción desconocida")

        token = _mint_jwt(matricula=matricula, email=email, role=role)
        query = urlencode({"token": token, "return": "/auth/me"})
        return redirect(f"/auth/callback?{query}")


def _mint_jwt(*, matricula: str, email: str, role: Role) -> str:
    now = int(time.time())
    claims = {
        "sub": matricula,
        "email": email,
        "rol": _ROLE_TO_PROVIDER_CLAIM[role],
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(
        claims,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _bad_request(message: str) -> HttpResponse:
    return HttpResponse(message, status=400, content_type="text/plain; charset=utf-8")
