"""Download view for an individual ``ArchivoRespuesta``."""
from __future__ import annotations

from urllib.parse import quote
from uuid import UUID

from django.http import FileResponse, HttpRequest
from django.views import View

from _shared.request_actor import actor_from_request
from solicitudes.respuesta.dependencies import get_respuesta_service
from usuarios.permissions import LoginRequiredMixin


class DownloadArchivoRespuestaView(LoginRequiredMixin, View):
    def get(
        self,
        request: HttpRequest,
        folio: str,
        respuesta_id: UUID,
        archivo_id: UUID,
    ) -> FileResponse:
        actor = actor_from_request(request)
        dto, stream = get_respuesta_service().open_for_download(
            archivo_id, requester=actor
        )
        response = FileResponse(
            stream,
            as_attachment=True,
            filename=dto.nombre_original,
            content_type=dto.content_type,
        )
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(dto.nombre_original)}"
        )
        response["Content-Length"] = str(dto.size_bytes)
        return response
