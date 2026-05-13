"""Abstract interface for the on-demand PDF renderer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.pdf.schemas import PdfRenderResult
from usuarios.schemas import UserDTO


class PdfService(ABC):
    """Renders a solicitud as a PDF using its tipo's plantilla."""

    @abstractmethod
    def render_for_solicitud(self, folio: str, requester: UserDTO) -> PdfRenderResult:
        """Render the PDF for ``folio`` requested by ``requester``.

        Authorisation: solicitante can render only when ``estado == FINALIZADA``;
        personal (responsible role) and admin can render at any state.
        Raises:
        - SolicitudNotFound — folio does not exist
        - Unauthorized — requester is not solicitante / personal / admin
        - TipoHasNoPlantilla — tipo.plantilla is None
        - PlantillaTemplateError — plantilla syntax error at render time
        """

    @abstractmethod
    def render_sample(self, plantilla_id: UUID) -> PdfRenderResult:
        """Render a plantilla against synthetic context for admin preview.

        No solicitud, no real user — uses placeholder values so an admin can
        iterate on layout without creating a real solicitud first.
        Raises PlantillaNotFound / PlantillaTemplateError.
        """
