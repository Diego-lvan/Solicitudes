"""GET /admin/tipos/<uuid>/fields.json — used by the plantilla editor panel.

Returns the active tipo's dynamic fields as `[{slug, label, type}, ...]`. The
slug matches the key the PDF render context exposes under ``valores.<slug>``.
"""
from __future__ import annotations

from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.text import slugify
from django.views import View

from _shared.exceptions import AppError
from solicitudes.tipos.dependencies import get_tipo_service
from usuarios.permissions import AdminRequiredMixin


def _slug_for_label(label: str) -> str:
    return slugify(label).replace("-", "_") or "campo"


class TipoFieldsJsonView(AdminRequiredMixin, View):
    def get(self, request: HttpRequest, tipo_id: UUID) -> HttpResponse:
        service = get_tipo_service()
        try:
            tipo = service.get_for_admin(tipo_id)
        except AppError as exc:
            return JsonResponse(
                {"error": exc.user_message}, status=exc.http_status
            )
        items = [
            {
                "slug": _slug_for_label(field.label),
                "label": field.label,
                "type": field.field_type.value,
            }
            for field in tipo.fields
        ]
        return JsonResponse({"fields": items})
