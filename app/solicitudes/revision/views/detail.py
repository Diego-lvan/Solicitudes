"""Revision detail view — same content as intake/detail plus action buttons."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.request_actor import actor_from_request
from solicitudes.lifecycle.constants import Estado
from solicitudes.revision.dependencies import get_review_service
from solicitudes.revision.forms.transition_form import TransitionForm
from solicitudes.revision.permissions import ReviewerRequiredMixin


class RevisionDetailView(ReviewerRequiredMixin, View):
    template_name = "solicitudes/revision/detail.html"

    def get(self, request: HttpRequest, folio: str) -> HttpResponse:
        actor = actor_from_request(request)
        detail = get_review_service().get_detail_for_personal(folio, actor.role)
        return render(
            request,
            self.template_name,
            {
                "detail": detail,
                "form": TransitionForm(),
                "can_atender": detail.estado is Estado.CREADA,
                "can_finalizar": detail.estado is Estado.EN_PROCESO,
                "can_cancelar": detail.estado in (Estado.CREADA, Estado.EN_PROCESO),
            },
        )
