"""Handler-side view: create a response batch."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from _shared.request_actor import actor_from_request
from solicitudes.respuesta.dependencies import get_respuesta_service
from solicitudes.respuesta.forms.respuesta_upload_form import RespuestaUploadForm
from solicitudes.respuesta.schemas import CreateRespuestaInput, UploadedFile
from solicitudes.revision.permissions import ReviewerRequiredMixin


class CreateRespuestaView(ReviewerRequiredMixin, View):
    """POST-only handler that builds a :class:`CreateRespuestaInput` and
    calls the service. Redirects back to the revision detail with a flash."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, folio: str) -> HttpResponse:
        actor = actor_from_request(request)
        form = RespuestaUploadForm(request.POST, request.FILES)
        target = reverse("solicitudes:revision:detail", args=[folio])

        if not form.is_valid():
            for err_list in form.errors.values():
                for err in err_list:
                    messages.error(request, err)
            return redirect(target)

        cleaned = form.cleaned_data
        files = cleaned.get("archivos_list", [])
        archivos = [
            UploadedFile(
                nombre_original=f.name or "archivo",
                content_type=f.content_type or "application/octet-stream",
                size_bytes=f.size or 0,
                content=f.read(),
            )
            for f in files
        ]
        try:
            input_dto = CreateRespuestaInput(
                folio=folio,
                actor_matricula=actor.matricula,
                actor_role=actor.role.value,
                comentario=cleaned.get("comentario", ""),
                archivos=archivos,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(target)

        try:
            get_respuesta_service().create_batch(input_dto)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(target)

        messages.success(request, "Respuesta adjuntada.")
        return redirect(target)
