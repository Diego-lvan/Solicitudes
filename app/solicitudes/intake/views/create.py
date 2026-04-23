"""Create-solicitud view — bound dynamic form + comprobante + persistence."""
from __future__ import annotations

import logging
from uuid import UUID

from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from _shared.request_actor import actor_from_request
from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.dependencies import (
    get_archivo_service,
    get_file_storage,
)
from solicitudes.intake.dependencies import get_intake_service, get_mentor_service
from solicitudes.intake.forms.intake_form import COMPROBANTE_FIELD
from solicitudes.intake.permissions import CreatorRequiredMixin
from solicitudes.intake.schemas import CreateSolicitudInput

logger = logging.getLogger(__name__)


def _field_id_from_attr(name: str) -> UUID | None:
    """Map ``"field_<32-hex>"`` back to a UUID; return ``None`` for other keys."""
    if not name.startswith("field_"):
        return None
    try:
        return UUID(name.removeprefix("field_"))
    except ValueError:
        return None


class CreateSolicitudView(CreatorRequiredMixin, View):
    template_name = "solicitudes/intake/create.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        actor = actor_from_request(request)
        is_mentor = get_mentor_service().is_mentor(actor.matricula)
        tipo, form_cls = get_intake_service().get_intake_form(
            slug, role=actor.role, is_mentor=is_mentor
        )
        return render(
            request, self.template_name, {"tipo": tipo, "form": form_cls()}
        )

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        actor = actor_from_request(request)
        service = get_intake_service()
        archivos = get_archivo_service()
        storage = get_file_storage()
        is_mentor = get_mentor_service().is_mentor(actor.matricula)

        tipo, form_cls = service.get_intake_form(
            slug, role=actor.role, is_mentor=is_mentor
        )
        form = form_cls(request.POST, request.FILES)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"tipo": tipo, "form": form},
                status=400,
            )

        valores = form.to_values_dict()  # type: ignore[attr-defined]
        input_dto = CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula=actor.matricula,
            valores=valores,
            is_mentor_at_creation=is_mentor,
        )

        # ``cleanup_pending`` is safe to call on success too — on success the
        # storage's on_commit hook already drained the per-thread pending
        # list, so this becomes a no-op. ``try/finally`` keeps the view free
        # of bare ``except Exception`` per architecture rules.
        try:
            try:
                with transaction.atomic():
                    detail = service.create(input_dto, actor=actor)
                    # Persist file fields + comprobante inside the same outer
                    # atomic block so a failure rolls back the Solicitud too.
                    for name in request.FILES:
                        uploaded = request.FILES[name]
                        if not isinstance(uploaded, UploadedFile):
                            continue
                        if name == COMPROBANTE_FIELD:
                            archivos.store_for_solicitud(
                                folio=detail.folio,
                                field_id=None,
                                kind=ArchivoKind.COMPROBANTE,
                                uploaded_file=uploaded,
                                uploader=actor,
                            )
                            continue
                        field_id = _field_id_from_attr(name)
                        if field_id is None:
                            continue
                        archivos.store_for_solicitud(
                            folio=detail.folio,
                            field_id=field_id,
                            kind=ArchivoKind.FORM,
                            uploaded_file=uploaded,
                            uploader=actor,
                        )
            except AppError as exc:
                form.add_error(None, exc.user_message)
                return render(
                    request,
                    self.template_name,
                    {"tipo": tipo, "form": form},
                    status=exc.http_status,
                )
        finally:
            storage.cleanup_pending()

        messages.success(request, f"Solicitud creada con folio {detail.folio}.")
        return redirect(
            reverse("solicitudes:intake:detail", kwargs={"folio": detail.folio})
        )
