"""Queue view — lists solicitudes assigned to the personal's role."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.pagination import PageRequest
from _shared.request_actor import actor_from_request
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudFilter
from solicitudes.revision.dependencies import get_review_service
from solicitudes.revision.permissions import ReviewerRequiredMixin


class QueueView(ReviewerRequiredMixin, View):
    template_name = "solicitudes/revision/queue.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        actor = actor_from_request(request)
        filters = self._read_filters(request)
        page_req = self._read_page(request)
        page = get_review_service().list_assigned(
            actor.role, page=page_req, filters=filters
        )
        return render(
            request,
            self.template_name,
            {
                "page": page,
                "filters": filters,
                "estados": list(Estado),
                "role": actor.role,
            },
        )

    @staticmethod
    def _read_filters(request: HttpRequest) -> SolicitudFilter:
        params = request.GET
        estado_str = params.get("estado") or None
        tipo_id_str = params.get("tipo") or None
        return SolicitudFilter(
            estado=Estado(estado_str) if estado_str else None,
            tipo_id=UUID(tipo_id_str) if tipo_id_str else None,
            folio_contains=params.get("folio") or None,
            solicitante_contains=params.get("solicitante") or None,
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
