"""Edit-tipo view (admin)."""
from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from pydantic import ValidationError as PydValidationError

from _shared.exceptions import AppError
from solicitudes.tipos.dependencies import get_tipo_service
from solicitudes.tipos.forms import FieldFormSet, TipoForm
from solicitudes.tipos.views._helpers import (
    build_update_input,
    fieldset_initial_from_dto,
)
from usuarios.permissions import AdminRequiredMixin


class TipoEditView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/tipos/form.html"

    def get(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        service = get_tipo_service()
        tipo = service.get_for_admin(tipo_id)
        tipo_form = TipoForm(
            initial={
                "nombre": tipo.nombre,
                "descripcion": tipo.descripcion,
                "responsible_role": tipo.responsible_role.value,
                "creator_roles": [r.value for r in tipo.creator_roles],
                "requires_payment": tipo.requires_payment,
                "mentor_exempt": tipo.mentor_exempt,
            }
        )
        field_formset = FieldFormSet(
            initial=fieldset_initial_from_dto(tipo.fields),
            prefix="fields",
        )
        return render(
            request,
            self.template_name,
            {
                "tipo": tipo,
                "tipo_form": tipo_form,
                "field_formset": field_formset,
                "form_title": f"Editar «{tipo.nombre}»",
                "submit_label": "Guardar cambios",
            },
        )

    def post(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        tipo_form = TipoForm(request.POST)
        field_formset = FieldFormSet(request.POST, prefix="fields")

        # Re-fetch the tipo so the template can render the heading even on error.
        # If the id no longer resolves (stale URL, concurrent delete), bail out
        # cleanly rather than leaking the form submission into a 404 page.
        service = get_tipo_service()
        try:
            tipo = service.get_for_admin(tipo_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:tipos:list"))

        if not (tipo_form.is_valid() and field_formset.is_valid()):
            return render(
                request,
                self.template_name,
                {
                    "tipo": tipo,
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": f"Editar «{tipo.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=400,
            )

        try:
            input_dto = build_update_input(tipo_id, tipo_form, field_formset)
        except PydValidationError as exc:
            for err in exc.errors():
                tipo_form.add_error(None, err.get("msg", "Datos inválidos."))
            return render(
                request,
                self.template_name,
                {
                    "tipo": tipo,
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": f"Editar «{tipo.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=400,
            )

        try:
            dto = service.update(input_dto)
        except AppError as exc:
            tipo_form.add_error(None, exc.user_message)
            return render(
                request,
                self.template_name,
                {
                    "tipo": tipo,
                    "tipo_form": tipo_form,
                    "field_formset": field_formset,
                    "form_title": f"Editar «{tipo.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=exc.http_status,
            )

        messages.success(request, f"Tipo «{dto.nombre}» actualizado.")
        return redirect(
            reverse("solicitudes:tipos:detail", kwargs={"tipo_id": dto.id})
        )
