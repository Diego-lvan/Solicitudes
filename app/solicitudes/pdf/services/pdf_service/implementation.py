"""Default PdfService implementation — renders solicitudes as PDFs on demand."""
from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.template import TemplateSyntaxError, engines
from django.utils.text import slugify

from _shared.exceptions import AppError, Unauthorized
from _shared.pdf import render_pdf
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.pdf.context import (
    assemble_html,
    build_render_context,
    build_synthetic_context,
)
from solicitudes.pdf.exceptions import PlantillaTemplateError, TipoHasNoPlantilla
from solicitudes.pdf.repositories.plantilla.interface import PlantillaRepository
from solicitudes.pdf.schemas import PdfRenderResult
from solicitudes.pdf.services.pdf_service.interface import PdfService
from solicitudes.plantilla_assets.schemas import PlantillaAssetDTO
from solicitudes.plantilla_assets.services.asset_service.interface import (
    AssetService,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO
from usuarios.services.user_service.interface import UserService

logger = logging.getLogger(__name__)


class DefaultPdfService(PdfService):
    """Composes lifecycle + plantilla repo + WeasyPrint into a deterministic
    on-demand PDF renderer.

    Owns:
    - Authorisation: who is allowed to render at which estado
    - Variable resolution: ``solicitante``, ``solicitud``, ``valores``, ``assets``, ``now``
    - Determinism: ``pdf_identifier`` is derived from folio (or plantilla id)
      and assets are embedded as ``data:`` URIs so byte-stability holds even
      across deployments (assuming the source files are unchanged).
    """

    def __init__(
        self,
        *,
        lifecycle_service: LifecycleService,
        plantilla_repository: PlantillaRepository,
        user_service: UserService,
        asset_service: AssetService,
        static_root: str | None = None,
    ) -> None:
        self._lifecycle = lifecycle_service
        self._plantillas = plantilla_repository
        self._users = user_service
        self._assets = asset_service
        self._static_root = static_root

    def render_for_solicitud(self, folio: str, requester: UserDTO) -> PdfRenderResult:
        detail = self._lifecycle.get_detail(folio)

        self._authorise(
            detail_estado=detail.estado,
            detail_solicitante_matricula=detail.solicitante.matricula,
            requester=requester,
        )

        if detail.tipo.plantilla_id is None:
            raise TipoHasNoPlantilla(f"tipo={detail.tipo.slug}")
        plantilla = self._plantillas.get_by_id(detail.tipo.plantilla_id)

        solicitante = self._users.get_by_matricula(detail.solicitante.matricula)

        assets_map = self._resolve_assets(plantilla.id)

        ctx = build_render_context(
            solicitud=detail,
            solicitante=solicitante,
            now=datetime.now(UTC),
            assets=assets_map,
        )
        try:
            body_html = engines["django"].from_string(plantilla.html).render(ctx)
        except TemplateSyntaxError as exc:
            raise PlantillaTemplateError(field_errors={"html": [str(exc)]}) from exc

        full_html = assemble_html(body_html, plantilla.css)
        pdf_bytes = render_pdf(
            full_html,
            base_url=self._static_root,
            pdf_identifier=folio.encode("utf-8"),
        )

        suggested = f"{slugify(detail.tipo.nombre) or 'solicitud'}-{folio}.pdf"
        logger.info(
            "Rendered PDF",
            extra={"folio": folio, "bytes": len(pdf_bytes), "by": requester.matricula},
        )
        return PdfRenderResult(
            folio=folio, bytes_=pdf_bytes, suggested_filename=suggested
        )

    def render_sample(self, plantilla_id: UUID) -> PdfRenderResult:
        """Render a plantilla against synthetic context for admin preview."""
        plantilla = self._plantillas.get_by_id(plantilla_id)
        assets_map = self._resolve_assets(plantilla_id)
        ctx = build_synthetic_context(now=datetime.now(UTC), assets=assets_map)
        try:
            body_html = engines["django"].from_string(plantilla.html).render(ctx)
        except TemplateSyntaxError as exc:
            raise PlantillaTemplateError(field_errors={"html": [str(exc)]}) from exc

        full_html = assemble_html(body_html, plantilla.css)
        pdf_bytes = render_pdf(
            full_html,
            base_url=self._static_root,
            pdf_identifier=str(plantilla_id).encode("ascii"),
        )
        return PdfRenderResult(
            folio="PREVIEW",
            bytes_=pdf_bytes,
            suggested_filename=f"preview-{slugify(plantilla.nombre) or 'plantilla'}.pdf",
        )

    # ---- helpers ----

    def _resolve_assets(self, plantilla_id: UUID | None) -> dict[str, str]:
        # Narrow catch: AppError signals a known asset-service failure; we
        # degrade gracefully so a borked asset table never blocks a PDF
        # render. DB and other infrastructure errors are intentionally not
        # swallowed — they bubble to the middleware.
        try:
            dtos = self._assets.list_for_render(plantilla_id)
        except AppError:
            logger.warning(
                "AssetService refused to list assets for plantilla %s",
                plantilla_id,
            )
            return {}
        return {dto.slug: asset_to_data_uri(dto) for dto in dtos}

    @staticmethod
    def _authorise(
        *,
        detail_estado: Estado,
        detail_solicitante_matricula: str,
        requester: UserDTO,
    ) -> None:
        # Plantilla PDF is a draft for personal/admin only (initiative 016).
        del detail_estado, detail_solicitante_matricula
        if requester.role is Role.ADMIN:
            return
        if requester.role in {
            Role.CONTROL_ESCOLAR,
            Role.RESPONSABLE_PROGRAMA,
        }:
            return
        raise Unauthorized("No puedes generar el PDF de esta solicitud.")


def asset_to_data_uri(dto: PlantillaAssetDTO) -> str:
    """Read the stored file and return a ``data:<mime>;base64,...`` URI.

    On read failure (file moved or deleted), returns an empty string so the
    plantilla renders ``<img src="">`` instead of crashing.
    """
    media_root = Path(getattr(settings, "MEDIA_ROOT", ""))
    file_path = media_root / dto.file_path
    try:
        with open(file_path, "rb") as fh:
            raw = fh.read()
    except (FileNotFoundError, OSError):
        logger.warning(
            "Asset file missing, rendering empty src",
            extra={"slug": dto.slug, "path": str(file_path)},
        )
        return ""
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{dto.mime_type};base64,{b64}"
