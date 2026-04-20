"""Tipo detail view — read-only with a dynamic-form preview."""
from __future__ import annotations

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from solicitudes.formularios.builder import build_django_form
from solicitudes.tipos.dependencies import get_tipo_service
from usuarios.permissions import AdminRequiredMixin


class TipoDetailView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/tipos/detail.html"

    def get(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        service = get_tipo_service()
        tipo = service.get_for_admin(tipo_id)

        preview_form = None
        if tipo.activo and tipo.fields:
            snapshot = service.snapshot(tipo_id)
            preview_form = build_django_form(snapshot)()

        return render(
            request,
            self.template_name,
            {
                "tipo": tipo,
                "preview_form": preview_form,
            },
        )
