"""Plantilla detail view (admin) — read-only with embedded sample-PDF preview."""
from __future__ import annotations

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from solicitudes.pdf.dependencies import get_plantilla_service
from usuarios.permissions import AdminRequiredMixin


class PlantillaDetailView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/detail.html"

    def get(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        plantilla = get_plantilla_service().get(plantilla_id)
        return render(request, self.template_name, {"plantilla": plantilla})
