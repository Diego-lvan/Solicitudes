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
from solicitudes.pdf.views._editor_context import panel_variables
from usuarios.permissions import AdminRequiredMixin


class PlantillaCreateView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantillas/form.html"

    def _ctx(self, **extra: object) -> dict[str, object]:
        ctx: dict[str, object] = {
            "form_title": "Nueva plantilla",
            "submit_label": "Crear plantilla",
            "tipo_id": self.request.GET.get("tipo_id") or "",  # type: ignore[attr-defined]
        }
        ctx.update(panel_variables())
        ctx.update(extra)
        return ctx

    def get(self, request: HttpRequest) -> HttpResponse:
        self.request = request  # type: ignore[attr-defined]
        return render(request, self.template_name, self._ctx(form=PlantillaForm()))

    def post(self, request: HttpRequest) -> HttpResponse:
        form = PlantillaForm(request.POST)
        if not form.is_valid():
            self.request = request  # type: ignore[attr-defined]
            return render(
                request, self.template_name, self._ctx(form=form), status=400
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
            self.request = request  # type: ignore[attr-defined]
            return render(
                request,
                self.template_name,
                self._ctx(form=form),
                status=exc.http_status,
            )
        except AppError as exc:
            form.add_error(None, exc.user_message)
            self.request = request  # type: ignore[attr-defined]
            return render(
                request,
                self.template_name,
                self._ctx(form=form),
                status=exc.http_status,
            )

        messages.success(request, f"Plantilla «{dto.nombre}» creada.")
        return redirect(
            reverse("solicitudes:plantillas:detail", kwargs={"plantilla_id": dto.id})
        )
