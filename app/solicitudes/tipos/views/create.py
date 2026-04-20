"""Create-tipo view (admin)."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from pydantic import ValidationError as PydValidationError

from _shared.exceptions import AppError
from solicitudes.tipos.dependencies import get_tipo_service
from solicitudes.tipos.forms import FieldFormSet, TipoForm
from solicitudes.tipos.views._helpers import build_create_input
from usuarios.permissions import AdminRequiredMixin


class TipoCreateView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/tipos/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                "tipo_form": TipoForm(),
                "field_formset": FieldFormSet(prefix="fields"),
                "form_title": "Nuevo tipo de solicitud",
                "submit_label": "Crear tipo",
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        tipo_form = TipoForm(request.POST)
        field_formset = FieldFormSet(request.POST, prefix="fields")

        if not (tipo_form.is_valid() and field_formset.is_valid()):
            return render(
                request,
                self.template_name,
                {
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": "Nuevo tipo de solicitud",
                    "submit_label": "Crear tipo",
                },
                status=400,
            )

        try:
            input_dto = build_create_input(tipo_form, field_formset)
        except PydValidationError as exc:
            for err in exc.errors():
                tipo_form.add_error(None, err.get("msg", "Datos inválidos."))
            return render(
                request,
                self.template_name,
                {
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": "Nuevo tipo de solicitud",
                    "submit_label": "Crear tipo",
                },
                status=400,
            )

        service = get_tipo_service()
        try:
            dto = service.create(input_dto)
        except AppError as exc:
            tipo_form.add_error(None, exc.user_message)
            return render(
                request,
                self.template_name,
                {
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": "Nuevo tipo de solicitud",
                    "submit_label": "Crear tipo",
                },
                status=exc.http_status,
            )

        messages.success(request, f"Tipo «{dto.nombre}» creado correctamente.")
        return redirect(
            reverse("solicitudes:tipos:detail", kwargs={"tipo_id": dto.id})
        )
