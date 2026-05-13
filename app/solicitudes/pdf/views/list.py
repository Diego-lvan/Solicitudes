"""Admin list view for plantillas."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from solicitudes.pdf.dependencies import get_plantilla_service
from usuarios.permissions import AdminRequiredMixin


class PlantillaListView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        only_active = request.GET.get("only_active") == "1"
        rows = get_plantilla_service().list(only_active=only_active)
        return render(
            request,
            self.template_name,
            {"plantillas": rows, "only_active": only_active},
        )
