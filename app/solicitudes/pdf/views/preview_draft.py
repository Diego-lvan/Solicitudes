"""Endpoint: POST /admin/plantillas/preview/

Renders HTML+CSS sent in the request body against a synthetic context, returning
an iframe-friendly HTML response. Optionally persists the draft into the
session so the "Ver PDF real" button can read it back.

Errors at template parse or render time are returned as 200 with an inline
red banner — the editor's iframe needs to render the body, and HTTP errors
would prevent the admin from seeing what went wrong.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.template import Context, Template, TemplateSyntaxError
from django.utils.html import escape
from django.views import View

from _shared.exceptions import AppError
from solicitudes.pdf.context import assemble_html, build_synthetic_context
from solicitudes.pdf.services.pdf_service.implementation import (
    asset_to_data_uri,
)
from solicitudes.plantilla_assets.dependencies import get_asset_service
from usuarios.permissions import AdminRequiredMixin

logger = logging.getLogger(__name__)

_SESSION_KEY = "plantilla_draft"


def _parse_uuid(raw: object) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return None


class PlantillaPreviewDraftView(AdminRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return self._error("Cuerpo JSON inválido.")

        html_body = str(payload.get("html") or "")
        css_body = str(payload.get("css") or "")
        plantilla_uuid = _parse_uuid(payload.get("plantilla_id") or None)

        assets_map = self._resolve_assets(plantilla_uuid)
        ctx = build_synthetic_context(now=datetime.now(UTC), assets=assets_map)

        rendered = self._render_body(html_body, ctx)
        if isinstance(rendered, HttpResponse):
            return rendered

        full_html = assemble_html(rendered, css_body)

        if request.GET.get("persist") == "1":
            request.session[_SESSION_KEY] = {
                "html": html_body,
                "css": css_body,
                "plantilla_id": str(plantilla_uuid) if plantilla_uuid else None,
            }

        resp = HttpResponse(full_html, content_type="text/html; charset=utf-8")
        resp["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "img-src data: https: 'self'; font-src data:"
        )
        resp["X-Frame-Options"] = "SAMEORIGIN"
        return resp

    @staticmethod
    def _resolve_assets(plantilla_uuid: UUID | None) -> dict[str, str]:
        # Resolve assets so {{ assets.<slug> }} works in the preview. Narrow
        # to AppError so infra failures bubble to middleware.
        asset_service = get_asset_service()
        try:
            asset_dtos = asset_service.list_for_render(plantilla_uuid)
            return {dto.slug: asset_to_data_uri(dto) for dto in asset_dtos}
        except AppError:
            logger.warning("AssetService refused list_for_render for preview")
            return {}

    def _render_body(
        self, html_body: str, ctx: dict[str, object]
    ) -> str | HttpResponse:
        try:
            tpl = Template(html_body)
            return tpl.render(Context(ctx))
        except TemplateSyntaxError as exc:
            return self._error(f"Error de sintaxis: {exc}")
        except Exception as exc:
            return self._error(f"Error al renderizar: {exc}")

    @staticmethod
    def _error(message: str) -> HttpResponse:
        safe = escape(message)
        body = (
            "<!doctype html><html><body "
            "style=\"font-family:ui-sans-serif,system-ui;padding:1rem;color:#111\">"
            "<div role=\"alert\" "
            "style=\"border:1px solid #dc2626;background:#fef2f2;color:#991b1b;"
            "padding:0.75rem;border-radius:6px;font-size:0.875rem\">"
            "<strong>Error de plantilla</strong>"
            f"<pre style=\"margin:0.5rem 0 0;white-space:pre-wrap\">{safe}</pre>"
            "</div></body></html>"
        )
        resp = HttpResponse(body, content_type="text/html; charset=utf-8", status=200)
        resp["X-Frame-Options"] = "SAMEORIGIN"
        return resp
