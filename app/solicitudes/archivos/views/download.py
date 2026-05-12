"""Stream a stored archivo to the requester (owner / responsible / admin)."""
from __future__ import annotations

from urllib.parse import quote
from uuid import UUID

from django.http import FileResponse, HttpRequest
from django.views import View

from _shared.request_actor import actor_from_request
from solicitudes.archivos.dependencies import get_archivo_service
from usuarios.permissions import LoginRequiredMixin


class DownloadArchivoView(LoginRequiredMixin, View):
    def get(
        self, request: HttpRequest, archivo_id: UUID
    ) -> FileResponse:
        actor = actor_from_request(request)
        dto, stream = get_archivo_service().open_for_download(
            archivo_id, actor
        )
        # FileResponse closes the underlying stream when the response finishes.
        response = FileResponse(
            stream,
            as_attachment=True,
            filename=dto.original_filename,
            content_type=dto.content_type,
        )
        # Defensive: ensure the encoded filename header includes UTF-8 fallback
        # for filenames with non-ASCII characters (Spanish accents, etc.).
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(dto.original_filename)}"
        )
        response["Content-Length"] = str(dto.size_bytes)
        return response
