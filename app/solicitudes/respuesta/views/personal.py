"""Handler-side view: create a response batch."""
from __future__ import annotations

from typing import Any

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


def _flash_form_errors(request: HttpRequest, form: RespuestaUploadForm) -> None:
    for err_list in form.errors.values():
        for err in err_list:
            messages.error(request, err)


def _build_uploaded_files(files: list[Any]) -> list[UploadedFile]:
    return [
        UploadedFile(
            nombre_original=f.name or "archivo",
            content_type=f.content_type or "application/octet-stream",
            size_bytes=f.size or 0,
            content=f.read(),
        )
        for f in files
    ]


class CreateRespuestaView(ReviewerRequiredMixin, View):
    """POST-only handler that builds a :class:`CreateRespuestaInput` and
    calls the service. Redirects back to the revision detail with a flash."""

    # Django's View declares this as an instance attribute; a ClassVar annotation
    # (what RUF012 wants) conflicts with that base declaration under mypy.
    http_method_names = ["post"]  # noqa: RUF012

    def post(self, request: HttpRequest, folio: str) -> HttpResponse:
        actor = actor_from_request(request)
        form = RespuestaUploadForm(request.POST, request.FILES)
        target = reverse("solicitudes:revision:detail", args=[folio])

        if not form.is_valid():
            _flash_form_errors(request, form)
            return redirect(target)

        cleaned = form.cleaned_data
        archivos = _build_uploaded_files(cleaned.get("archivos_list", []))
        try:
            input_dto = CreateRespuestaInput(
                folio=folio,
                actor_matricula=actor.matricula,
                actor_role=actor.role.value,
                comentario=cleaned.get("comentario", ""),
                archivos=archivos,
            )
        except ValueError as exc:  # pragma: no cover - el formulario ya valida estas invariantes
            messages.error(request, str(exc))
            return redirect(target)

        try:
            get_respuesta_service().create_batch(input_dto)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(target)

        messages.success(request, "Respuesta adjuntada.")
        return redirect(target)
