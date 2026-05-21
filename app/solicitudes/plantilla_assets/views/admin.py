"""Admin views for the plantilla_assets feature.

- Global gallery (list, upload, delete)
- Per-plantilla upload (called from the editor's modal)
- JSON endpoint consumed by the editor's lateral panel
"""
from __future__ import annotations

import json
from uuid import UUID

from django.contrib import messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError, DomainValidationError
from solicitudes.plantilla_assets.dependencies import get_asset_service
from solicitudes.plantilla_assets.forms import AssetUploadForm
from solicitudes.plantilla_assets.permissions import AdminRequiredMixin
from solicitudes.plantilla_assets.schemas import (
    AssetScope,
    CreateAssetInput,
    PlantillaAssetRow,
)


def _accepts_json(request: HttpRequest) -> bool:
    accept = (request.headers.get("Accept") or "").lower()
    xrw = (request.headers.get("X-Requested-With") or "").lower()
    return "application/json" in accept or xrw == "xmlhttprequest"


def _row_to_json(row: PlantillaAssetRow) -> dict[str, object]:
    return {
        "id": str(row.id),
        "slug": row.slug,
        "nombre": row.nombre,
        "scope": row.scope.value,
        "plantilla_id": str(row.plantilla_id) if row.plantilla_id else None,
        "thumb_url": row.thumb_url,
        "snippet": '<img src="{{ assets.' + row.slug + ' }}">',
        "size_bytes": row.size_bytes,
    }


class AssetListView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantilla_assets/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        service = get_asset_service()
        assets = service.list_global()
        return render(
            request,
            self.template_name,
            {"assets": assets, "form": AssetUploadForm()},
        )


class AssetUploadView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantilla_assets/list.html"

    def post(self, request: HttpRequest) -> HttpResponse:
        form = AssetUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._respond_form_errors(request, form)

        file = form.cleaned_data["imagen"]
        input_dto = CreateAssetInput(
            nombre=form.cleaned_data["nombre"],
            scope=AssetScope.GLOBAL,
            plantilla_id=None,
            file_bytes=file.read(),
            original_filename=file.name,
            mime_type=(file.content_type or "").lower(),
            created_by_id=request.user.pk,
        )
        return self._create(request, input_dto)

    def _create(
        self, request: HttpRequest, input_dto: CreateAssetInput
    ) -> HttpResponse:
        try:
            row = get_asset_service().create(input_dto)
        except DomainValidationError as exc:
            if _accepts_json(request):
                return JsonResponse(
                    {"error": exc.user_message, "field_errors": exc.field_errors},
                    status=exc.http_status,
                )
            for field, errs in exc.field_errors.items():
                for e in errs:
                    messages.error(request, f"{field}: {e}")
            return redirect(reverse("solicitudes:plantilla_assets:list"))
        except AppError as exc:
            if _accepts_json(request):
                return JsonResponse(
                    {"error": exc.user_message}, status=exc.http_status
                )
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:plantilla_assets:list"))

        if _accepts_json(request):
            return JsonResponse(_row_to_json(row), status=201)
        messages.success(request, f"Imagen «{row.nombre}» cargada.")
        return redirect(reverse("solicitudes:plantilla_assets:list"))

    def _respond_form_errors(
        self, request: HttpRequest, form: AssetUploadForm
    ) -> HttpResponse:
        if _accepts_json(request):
            return JsonResponse(
                {"error": "Datos inválidos", "field_errors": form.errors},
                status=422,
            )
        service = get_asset_service()
        return render(
            request,
            self.template_name,
            {"assets": service.list_global(), "form": form},
            status=400,
        )


class AssetUploadForPlantillaView(AdminRequiredMixin, View):
    """POST a new asset bound to a specific plantilla. Used by the editor modal."""

    def post(self, request: HttpRequest, plantilla_id: UUID) -> HttpResponse:
        form = AssetUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            if _accepts_json(request):
                return JsonResponse(
                    {"error": "Datos inválidos", "field_errors": form.errors},
                    status=422,
                )
            messages.error(request, "Datos inválidos.")
            return redirect(
                reverse(
                    "solicitudes:plantillas:edit",
                    kwargs={"plantilla_id": plantilla_id},
                )
            )

        file = form.cleaned_data["imagen"]
        input_dto = CreateAssetInput(
            nombre=form.cleaned_data["nombre"],
            scope=AssetScope.PLANTILLA,
            plantilla_id=plantilla_id,
            file_bytes=file.read(),
            original_filename=file.name,
            mime_type=(file.content_type or "").lower(),
            created_by_id=request.user.pk,
        )
        try:
            row = get_asset_service().create(input_dto)
        except DomainValidationError as exc:
            if _accepts_json(request):
                return JsonResponse(
                    {"error": exc.user_message, "field_errors": exc.field_errors},
                    status=exc.http_status,
                )
            for field, errs in exc.field_errors.items():
                for e in errs:
                    messages.error(request, f"{field}: {e}")
            return redirect(
                reverse(
                    "solicitudes:plantillas:edit",
                    kwargs={"plantilla_id": plantilla_id},
                )
            )
        except AppError as exc:
            if _accepts_json(request):
                return JsonResponse(
                    {"error": exc.user_message}, status=exc.http_status
                )
            messages.error(request, exc.user_message)
            return redirect(
                reverse(
                    "solicitudes:plantillas:edit",
                    kwargs={"plantilla_id": plantilla_id},
                )
            )

        if _accepts_json(request):
            return JsonResponse(_row_to_json(row), status=201)
        messages.success(request, f"Imagen «{row.nombre}» cargada.")
        return redirect(
            reverse(
                "solicitudes:plantillas:edit",
                kwargs={"plantilla_id": plantilla_id},
            )
        )


class AssetDeleteView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/plantilla_assets/confirm_delete.html"

    def get(self, request: HttpRequest, asset_id: UUID) -> HttpResponse:
        try:
            dto = get_asset_service().get(asset_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:plantilla_assets:list"))
        return render(request, self.template_name, {"asset": dto})

    def post(self, request: HttpRequest, asset_id: UUID) -> HttpResponse:
        try:
            get_asset_service().delete(asset_id)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("solicitudes:plantilla_assets:list"))
        messages.success(request, "Imagen eliminada.")
        return redirect(reverse("solicitudes:plantilla_assets:list"))


class AssetListJsonView(AdminRequiredMixin, View):
    """JSON feed for the editor's lateral panel."""

    def get(self, request: HttpRequest) -> HttpResponse:
        service = get_asset_service()
        plantilla_id_raw = request.GET.get("plantilla_id")
        plantilla_uuid: UUID | None = None
        if plantilla_id_raw:
            try:
                plantilla_uuid = UUID(plantilla_id_raw)
            except ValueError:
                plantilla_uuid = None
        global_rows = [_row_to_json(r) for r in service.list_global()]
        plantilla_rows: list[dict[str, object]] = []
        if plantilla_uuid is not None:
            plantilla_rows = [
                _row_to_json(r) for r in service.list_for_plantilla(plantilla_uuid)
            ]
        return JsonResponse({"global": global_rows, "plantilla": plantilla_rows})
