"""Owner-cancel view — POST-only, cancels a solicitud while still ``CREADA``."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from _shared.request_actor import actor_from_request
from solicitudes.intake.dependencies import get_intake_service
from solicitudes.intake.permissions import CreatorRequiredMixin


class CancelOwnView(CreatorRequiredMixin, View):
    def post(self, request: HttpRequest, folio: str) -> HttpResponse:
        actor = actor_from_request(request)
        observaciones = (request.POST.get("observaciones") or "").strip()
        try:
            get_intake_service().cancel_own(
                folio, actor=actor, observaciones=observaciones
            )
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(
                reverse("solicitudes:intake:detail", kwargs={"folio": folio})
            )

        messages.success(request, "Solicitud cancelada.")
        return redirect(reverse("solicitudes:intake:mis_solicitudes"))
