"""``GET /auth/logout`` — clears the session cookie and bounces to the provider."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View

from usuarios.constants import SESSION_COOKIE_NAME


class LogoutView(View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        target = settings.AUTH_PROVIDER_LOGOUT_URL or "/"
        response = redirect(target)
        response.delete_cookie(SESSION_COOKIE_NAME)
        return response
