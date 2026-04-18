"""``GET /auth/me`` — renders the current user's profile (debug aid + integration check)."""
from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from usuarios.permissions import LoginRequiredMixin


class MeView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # request.user_dto is set dynamically by JwtAuthenticationMiddleware on
        # every authenticated request; getattr avoids a static-typing complaint.
        user_dto = getattr(request, "user_dto", None)
        return render(request, "usuarios/me.html", {"user": user_dto})
