"""Soft-delete (deactivate) view for tipos."""
from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from solicitudes.tipos.dependencies import get_tipo_service
from usuarios.permissions import AdminRequiredMixin


class TipoDeactivateView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/tipos/confirm_deactivate.html"

    def get(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        service = get_tipo_service()
        tipo = service.get_for_admin(tipo_id)
        return render(request, self.template_name, {"tipo": tipo})

    def post(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        service = get_tipo_service()
        try:
            service.deactivate(tipo_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:tipos:list"))

        messages.success(request, "Tipo desactivado.")
        return redirect(reverse("solicitudes:tipos:list"))
