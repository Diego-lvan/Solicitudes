"""Default PdfService implementation — renders solicitudes as PDFs on demand."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from django.template import TemplateSyntaxError, engines
from django.utils.text import slugify

from _shared.exceptions import Unauthorized
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
from usuarios.constants import Role
from usuarios.schemas import UserDTO
from usuarios.services.user_service.interface import UserService

logger = logging.getLogger(__name__)


class DefaultPdfService(PdfService):
    """Composes lifecycle + plantilla repo + WeasyPrint into a deterministic
    on-demand PDF renderer.

    Owns:
    - Authorisation: who is allowed to render at which estado
    - Variable resolution: ``solicitante``, ``solicitud``, ``valores``, ``now``
    - Determinism: passes ``pdf_identifier=folio.encode()`` so two renders of
      the same folio under a frozen clock produce byte-identical bytes.
      Determinism holds *within* an environment; ``base_url`` resolves to the
      local ``STATIC_ROOT`` and a plantilla that references ``/static/foo``
      may produce different bytes across machines if the resolved file
      differs. Plantillas built for byte-stability should embed images as
      ``data:`` URIs (see plan OQ-006-1 resolution).
    """

    def __init__(
        self,
        *,
        lifecycle_service: LifecycleService,
        plantilla_repository: PlantillaRepository,
        user_service: UserService,
        static_root: str | None = None,
    ) -> None:
        self._lifecycle = lifecycle_service
        self._plantillas = plantilla_repository
        self._users = user_service
        self._static_root = static_root

    def render_for_solicitud(self, folio: str, requester: UserDTO) -> PdfRenderResult:
        # 1. Detail (raises SolicitudNotFound)
        detail = self._lifecycle.get_detail(folio)

        # 2. Authorise
        self._authorise(
            detail_estado=detail.estado,
            detail_solicitante_matricula=detail.solicitante.matricula,
            requester=requester,
        )

        # 3. Plantilla
        if detail.tipo.plantilla_id is None:
            raise TipoHasNoPlantilla(f"tipo={detail.tipo.slug}")
        plantilla = self._plantillas.get_by_id(detail.tipo.plantilla_id)

        # 4. Hydrated solicitante (PDF wants programa/semestre even if the
        # cached row missed them)
        solicitante = self._users.get_by_matricula(detail.solicitante.matricula)

        # 5. Render
        ctx = build_render_context(
            solicitud=detail,
            solicitante=solicitante,
            now=datetime.now(UTC),
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
        ctx = build_synthetic_context(now=datetime.now(UTC))
        try:
            body_html = engines["django"].from_string(plantilla.html).render(ctx)
        except TemplateSyntaxError as exc:
            raise PlantillaTemplateError(field_errors={"html": [str(exc)]}) from exc

        full_html = assemble_html(body_html, plantilla.css)
        # No solicitud → no folio. Use the plantilla id as the deterministic key
        # so two consecutive previews are byte-identical under a frozen clock.
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

    @staticmethod
    def _authorise(
        *,
        detail_estado: Estado,
        detail_solicitante_matricula: str,
        requester: UserDTO,
    ) -> None:
        is_owner = requester.matricula == detail_solicitante_matricula
        is_admin = requester.role is Role.ADMIN
        is_personal = requester.role in {
            Role.CONTROL_ESCOLAR,
            Role.RESPONSABLE_PROGRAMA,
        }
        if is_admin or is_personal:
            return
        if is_owner and detail_estado is Estado.FINALIZADA:
            return
        raise Unauthorized("No puedes generar el PDF de esta solicitud.")
