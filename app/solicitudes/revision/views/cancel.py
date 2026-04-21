"""Cancel-by-personal view — cancels CREADA or EN_PROCESO."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from solicitudes.revision.dependencies import get_review_service
from solicitudes.revision.forms.transition_form import TransitionForm
from solicitudes.revision.permissions import ReviewerRequiredMixin
from solicitudes.revision.views._helpers import actor_from_request


class CancelByPersonalView(ReviewerRequiredMixin, View):
    def post(self, request: HttpRequest, folio: str) -> HttpResponse:
        form = TransitionForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Las observaciones no son válidas.")
            return redirect(
                reverse("solicitudes:revision:detail", kwargs={"folio": folio})
            )
        try:
            get_review_service().cancel(
                folio,
                actor=actor_from_request(request),
                observaciones=form.cleaned_data["observaciones"],
            )
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(
                reverse("solicitudes:revision:detail", kwargs={"folio": folio})
            )
        messages.success(request, "Solicitud cancelada.")
        return redirect(
            reverse("solicitudes:revision:queue")
        )
