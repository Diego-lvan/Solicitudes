"""Create plantilla view (admin)."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError, DomainValidationError
from solicitudes.pdf.dependencies import get_plantilla_service
from solicitudes.pdf.forms import PlantillaForm
from solicitudes.pdf.schemas import CreatePlantillaInput
from usuarios.permissions import AdminRequiredMixin


class PlantillaCreateView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                "form": PlantillaForm(),
                "form_title": "Nueva plantilla",
                "submit_label": "Crear plantilla",
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = PlantillaForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "form_title": "Nueva plantilla",
                    "submit_label": "Crear plantilla",
                },
                status=400,
            )

        input_dto = CreatePlantillaInput(
            nombre=form.cleaned_data["nombre"],
            descripcion=form.cleaned_data["descripcion"],
            html=form.cleaned_data["html"],
            css=form.cleaned_data["css"],
            activo=form.cleaned_data["activo"],
        )
        service = get_plantilla_service()
        try:
            dto = service.create(input_dto)
        except DomainValidationError as exc:
            for field, errs in exc.field_errors.items():
                for e in errs:
                    form.add_error(field if field in form.fields else None, e)
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "form_title": "Nueva plantilla",
                    "submit_label": "Crear plantilla",
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
                    "form_title": "Nueva plantilla",
                    "submit_label": "Crear plantilla",
                },
                status=exc.http_status,
            )

        messages.success(request, f"Plantilla «{dto.nombre}» creada.")
        return redirect(
            reverse("solicitudes:plantillas:detail", kwargs={"plantilla_id": dto.id})
        )
