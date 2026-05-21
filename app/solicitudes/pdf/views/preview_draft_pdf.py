"""Endpoint: GET /admin/plantillas/preview/pdf/

Reads the draft persisted by PlantillaPreviewDraftView and renders it through
WeasyPrint, returning an inline PDF. The admin opens this in a new tab to
validate the real PDF render before saving.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template import Context, Template, TemplateSyntaxError
from django.views import View

from _shared.exceptions import AppError, DomainValidationError
from _shared.pdf import render_pdf
from solicitudes.pdf.context import assemble_html, build_synthetic_context
from solicitudes.pdf.services.pdf_service.implementation import (
    asset_to_data_uri,
)
from solicitudes.plantilla_assets.dependencies import get_asset_service
from usuarios.permissions import AdminRequiredMixin

logger = logging.getLogger(__name__)

_SESSION_KEY = "plantilla_draft"


class PlantillaPreviewDraftPdfView(AdminRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        draft = request.session.get(_SESSION_KEY)
        if not draft:
            raise DomainValidationError(
                "No hay borrador en la sesión.",
                field_errors={
                    "preview": [
                        "Abre primero el preview HTML antes de generar el PDF."
                    ]
                },
            )

        plantilla_id_raw = draft.get("plantilla_id")
        plantilla_uuid: UUID | None = None
        if plantilla_id_raw:
            try:
                plantilla_uuid = UUID(plantilla_id_raw)
            except ValueError:
                plantilla_uuid = None

        # Assets
        asset_service = get_asset_service()
        try:
            dtos = asset_service.list_for_render(plantilla_uuid)
            assets_map = {dto.slug: asset_to_data_uri(dto) for dto in dtos}
        except AppError:
            logger.warning("AssetService refused list_for_render for preview pdf")
            assets_map = {}

        ctx = build_synthetic_context(now=datetime.now(UTC), assets=assets_map)
        try:
            body_rendered = Template(draft.get("html") or "").render(Context(ctx))
        except TemplateSyntaxError as exc:
            raise DomainValidationError(
                "La plantilla tiene errores de sintaxis.",
                field_errors={"html": [str(exc)]},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise DomainValidationError(
                "Error al renderizar la plantilla.",
                field_errors={"html": [str(exc)]},
            ) from exc

        full_html = assemble_html(body_rendered, draft.get("css") or "")
        static_root = getattr(settings, "STATIC_ROOT", None) or None
        identifier = (plantilla_id_raw or "draft").encode("ascii", errors="ignore")
        pdf_bytes = render_pdf(
            full_html, base_url=static_root, pdf_identifier=identifier
        )
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="preview.pdf"'
        resp["X-Frame-Options"] = "SAMEORIGIN"
        return resp
