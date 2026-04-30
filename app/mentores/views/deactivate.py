"""Soft-delete (deactivate) view for mentors (admin)."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from mentores.dependencies import get_mentor_service
from mentores.permissions import AdminRequiredMixin


class DeactivateMentorView(AdminRequiredMixin, View):
    """Two-step soft-delete: GET shows confirmation, POST applies it."""

    template_name = "mentores/confirm_deactivate.html"

    def get(self, request: HttpRequest, matricula: str) -> HttpResponse:
        # No preflight — if the matricula is bogus, POST will surface
        # ``MentorNotFound`` with a friendly message and redirect.
        return render(request, self.template_name, {"matricula": matricula})

    def post(self, request: HttpRequest, matricula: str) -> HttpResponse:
        actor = getattr(request, "user_dto", None)
        if actor is None:
            return redirect(reverse("mentores:list"))
        service = get_mentor_service()
        try:
            service.deactivate(matricula, actor=actor)
        except AppError as exc:
            messages.error(request, exc.user_message)
            return redirect(reverse("mentores:list"))
        messages.success(request, f"Mentor «{matricula}» desactivado.")
        return redirect(reverse("mentores:list"))
