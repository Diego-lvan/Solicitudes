"""Create-solicitud view — bound dynamic form + comprobante + persistence."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from _shared.request_actor import actor_from_request
from solicitudes.intake.dependencies import get_intake_service, get_mentor_service
from solicitudes.intake.permissions import CreatorRequiredMixin
from solicitudes.intake.schemas import CreateSolicitudInput

logger = logging.getLogger(__name__)


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

        if request.FILES:
            # 005 will store these via ArchivoService.store_for_solicitud(folio, ...)
            # inside the same transaction as the row insert. Until 005 ships,
            # we accept the upload validation but discard the bytes — and surface
            # a warning to both the operator (log) and the user (flash) so a
            # missing comprobante or attachment doesn't silently surprise anyone.
            logger.warning(
                "intake.files_discarded",
                extra={
                    "tipo": tipo.slug,
                    "fields": list(request.FILES.keys()),
                    "reason": "ArchivoService not yet wired (005)",
                },
            )
            messages.warning(
                request,
                "Los archivos adjuntos aún no se almacenan; tu solicitud se "
                "registró sin ellos. Vuelve a adjuntarlos cuando el módulo "
                "de archivos esté disponible.",
            )

        input_dto = CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula=actor.matricula,
            valores=valores,
            is_mentor_at_creation=is_mentor,
        )

        try:
            detail = service.create(input_dto, actor=actor)
        except AppError as exc:
            form.add_error(None, exc.user_message)
            return render(
                request,
                self.template_name,
                {"tipo": tipo, "form": form},
                status=exc.http_status,
            )

        messages.success(request, f"Solicitud creada con folio {detail.folio}.")
        return redirect(
            reverse("solicitudes:intake:detail", kwargs={"folio": detail.folio})
        )
