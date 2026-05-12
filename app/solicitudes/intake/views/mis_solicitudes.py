"""``Mis solicitudes`` — owner-scoped list view for the solicitante."""
from __future__ import annotations

from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.pagination import PageRequest
from _shared.request_actor import actor_from_request
from solicitudes.intake.permissions import CreatorRequiredMixin
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.dependencies import get_lifecycle_service
from solicitudes.lifecycle.schemas import SolicitudFilter


class MisSolicitudesView(CreatorRequiredMixin, View):
    template_name = "solicitudes/intake/mis_solicitudes.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        actor = actor_from_request(request)
        filters = self._read_filters(request)
        page_req = self._read_page(request)
        page = get_lifecycle_service().list_for_solicitante(
            actor.matricula, page=page_req, filters=filters
        )
        return render(
            request,
            self.template_name,
            {"page": page, "filters": filters, "estados": list(Estado)},
        )

    @staticmethod
    def _read_filters(request: HttpRequest) -> SolicitudFilter:
        # Filter UI exposes folio, estado, and date range. ``tipo_id`` is not
        # surfaced here because the alumno's ``mis/`` view typically lists a
        # short, mixed set of solicitudes; adding a populated <select> for it
        # is deferred until the volume justifies the extra UI complexity.
        params = request.GET
        estado_str = params.get("estado") or None
        return SolicitudFilter(
            estado=Estado(estado_str) if estado_str else None,
            folio_contains=params.get("folio") or None,
            created_from=date.fromisoformat(params["desde"]) if params.get("desde") else None,
            created_to=date.fromisoformat(params["hasta"]) if params.get("hasta") else None,
        )

    @staticmethod
    def _read_page(request: HttpRequest) -> PageRequest:
        try:
            page = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        return PageRequest(page=max(1, page))
