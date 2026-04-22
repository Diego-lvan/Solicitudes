"""Edit plantilla view (admin)."""
from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError, DomainValidationError
from solicitudes.pdf.dependencies import get_plantilla_service
from solicitudes.pdf.forms import PlantillaForm
from solicitudes.pdf.schemas import UpdatePlantillaInput
from usuarios.permissions import AdminRequiredMixin


class PlantillaEditView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/form.html"

    def get(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        plantilla = get_plantilla_service().get(plantilla_id)
        form = PlantillaForm(
            initial={
                "nombre": plantilla.nombre,
                "descripcion": plantilla.descripcion,
                "html": plantilla.html,
                "css": plantilla.css,
                "activo": plantilla.activo,
            }
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "plantilla": plantilla,
                "form_title": f"Editar «{plantilla.nombre}»",
                "submit_label": "Guardar cambios",
            },
        )

    def post(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        form = PlantillaForm(request.POST)
        service = get_plantilla_service()

        try:
            plantilla = service.get(plantilla_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:plantillas:list"))

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "plantilla": plantilla,
                    "form_title": f"Editar «{plantilla.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=400,
            )

        input_dto = UpdatePlantillaInput(
            id=plantilla_id,
            nombre=form.cleaned_data["nombre"],
            descripcion=form.cleaned_data["descripcion"],
            html=form.cleaned_data["html"],
            css=form.cleaned_data["css"],
            activo=form.cleaned_data["activo"],
        )
        try:
            dto = service.update(input_dto)
        except DomainValidationError as exc:
            for field, errs in exc.field_errors.items():
                for e in errs:
                    form.add_error(field if field in form.fields else None, e)
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "plantilla": plantilla,
                    "form_title": f"Editar «{plantilla.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=exc.http_status,
            )
        except AppError as exc:
            form.add_error(None, exc.user_message)
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "plantilla": plantilla,
                    "form_title": f"Editar «{plantilla.nombre}»",
                    "submit_label": "Guardar cambios",
                },
                status=exc.http_status,
            )

        messages.success(request, f"Plantilla «{dto.nombre}» actualizada.")
        return redirect(
            reverse("solicitudes:plantillas:detail", kwargs={"plantilla_id": dto.id})
        )
