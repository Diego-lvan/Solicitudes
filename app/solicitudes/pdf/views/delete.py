"""Soft-delete (deactivate) view for plantillas."""
from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from solicitudes.pdf.dependencies import get_plantilla_service
from usuarios.permissions import AdminRequiredMixin


class PlantillaDeactivateView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/confirm_deactivate.html"

    def get(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        plantilla = get_plantilla_service().get(plantilla_id)
        return render(request, self.template_name, {"plantilla": plantilla})

    def post(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        try:
            get_plantilla_service().deactivate(plantilla_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:plantillas:list"))
        messages.success(request, "Plantilla desactivada.")
        return redirect(reverse("solicitudes:plantillas:list"))
