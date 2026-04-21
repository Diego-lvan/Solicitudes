"""Catalog view — lists tipos the current actor's role may file."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.request_actor import actor_from_request
from solicitudes.intake.dependencies import get_intake_service
from solicitudes.intake.permissions import CreatorRequiredMixin


class CatalogView(CreatorRequiredMixin, View):
    template_name = "solicitudes/intake/catalog.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        actor = actor_from_request(request)
        tipos = get_intake_service().list_creatable_tipos(actor.role)
        return render(request, self.template_name, {"tipos": tipos})
