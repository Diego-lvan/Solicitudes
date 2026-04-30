"""Read-only timeline of a single matrícula's mentorship history (admin)."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from mentores.dependencies import get_mentor_service
from mentores.exceptions import MentorNotFound
from mentores.permissions import AdminRequiredMixin


class MentorDetailView(AdminRequiredMixin, View):
    """Render the per-period timeline for ``matricula``.

    The matrícula has at least one period iff it has ever been a mentor; if
    ``get_history`` is empty, raise ``MentorNotFound`` (mapped to 404 by the
    error middleware).
    """

    template_name = "mentores/detail.html"

    def get(self, request: HttpRequest, matricula: str) -> HttpResponse:
        history = get_mentor_service().get_history(matricula)
        if not history:
            raise MentorNotFound(f"matricula={matricula}")
        is_currently_active = history[0].fecha_baja is None
        return render(
            request,
            self.template_name,
            {
                "matricula": matricula,
                "history": history,
                "is_currently_active": is_currently_active,
            },
        )
