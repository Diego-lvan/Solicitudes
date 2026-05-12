"""Solicitud detail view — owner, responsible-role personal, or admin."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.exceptions import Unauthorized
from _shared.request_actor import actor_from_request
from solicitudes.archivos.dependencies import get_archivo_service
from solicitudes.lifecycle.dependencies import get_lifecycle_service
from usuarios.constants import Role
from usuarios.permissions import LoginRequiredMixin


class SolicitudDetailView(LoginRequiredMixin, View):
    template_name = "solicitudes/intake/detail.html"

    def get(self, request: HttpRequest, folio: str) -> HttpResponse:
        actor = actor_from_request(request)
        detail = get_lifecycle_service().get_detail(folio)

        is_owner = detail.solicitante.matricula == actor.matricula
        is_responsible = actor.role == detail.tipo.responsible_role
        is_admin = actor.role is Role.ADMIN

        if not (is_owner or is_responsible or is_admin):
            raise Unauthorized("No puedes ver esta solicitud.")

        archivos = get_archivo_service().list_for_solicitud(folio)

        return render(
            request,
            self.template_name,
            {
                "detail": detail,
                "is_owner": is_owner,
                "can_act": is_responsible or is_admin,
                "archivos": archivos,
            },
        )
