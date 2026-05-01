"""Admin read-only detail page for a single user."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from usuarios.directory.dependencies import get_user_directory_service
from usuarios.directory.views._helpers import safe_return_path
from usuarios.permissions import AdminRequiredMixin


class DirectoryDetailView(AdminRequiredMixin, View):
    template_name = "usuarios/directory/detail.html"

    def get(self, request: HttpRequest, matricula: str) -> HttpResponse:
        detail = get_user_directory_service().get_detail(matricula)
        back_url = (
            safe_return_path(request.GET.get("return", ""))
            or reverse("usuarios:directory:list")
        )
        ctx = {"user_detail": detail, "back_url": back_url}
        return render(request, self.template_name, ctx)
