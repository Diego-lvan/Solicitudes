"""Manual add-mentor view (admin)."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from mentores.constants import MentorSource
from mentores.dependencies import get_mentor_service
from mentores.forms import AddMentorForm
from mentores.permissions import AdminRequiredMixin


class AddMentorView(AdminRequiredMixin, View):
    template_name = "mentores/add.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": AddMentorForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = AddMentorForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        actor = getattr(request, "user_dto", None)
        if actor is None:
            # Should never reach this branch — AdminRequiredMixin enforces auth.
            return render(request, self.template_name, {"form": form}, status=403)

        service = get_mentor_service()
        try:
            dto = service.add(
                matricula=form.cleaned_data["matricula"],
                fuente=MentorSource.MANUAL,
                nota=form.cleaned_data["nota"],
                actor=actor,
            )
        except AppError as exc:
            form.add_error(None, exc.user_message)
            return render(
                request, self.template_name, {"form": form}, status=exc.http_status
            )

        messages.success(
            request, f"Mentor «{dto.matricula}» registrado correctamente."
        )
        return redirect(reverse("mentores:list"))
