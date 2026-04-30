"""Bulk-deactivate-mentors view (admin) — two-step server-side confirm.

Single endpoint. Step 1 (POST without ``token``) renders the confirmation
template carrying a server-signed payload. Step 2 (POST with the token)
verifies the signature and applies the change via the service, attaches a
Django messages summary, and redirects to the list.

Why a signed token instead of plain hidden inputs:

- The plain-hidden-input approach lets a same-origin script skip the
  warning page entirely by POSTing ``confirmed=1`` directly. CSRF stops
  cross-site abuse, not same-origin scripted misuse. For the
  "Desactivar todos los activos" action — the destructive action of the
  whole module — the confirmation page is the only friction, so it must
  be enforced.
- ``django.core.signing`` gives us a tamper-proof, time-bound token using
  ``SECRET_KEY``. A 5-minute ``max_age`` means an admin who walked away
  cannot land back at a stale confirm page and click through.
- The token also carries the matrículas, so a tampered second-POST
  cannot expand or swap the target set after the warning page rendered.
"""
from __future__ import annotations

from django.contrib import messages
from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from mentores.dependencies import get_mentor_service
from mentores.permissions import AdminRequiredMixin
from mentores.schemas import BulkDeactivateResult


class BulkDeactivateMentorsView(AdminRequiredMixin, View):
    """POST-only endpoint for bulk closure of mentor periods."""

    template_name = "mentores/confirm_bulk_deactivate.html"

    # ``action`` discriminator values posted from the list page.
    ACTION_SELECTED = "selected"
    ACTION_ALL = "all"

    # ``signing`` namespacing prevents tokens from one feature being
    # accepted by another that happens to share the secret key.
    SIGNING_SALT = "mentores.bulk_deactivate"
    # 5 minutes is enough for a deliberate human review and short enough
    # that an abandoned tab can't be exploited to skip confirmation later.
    TOKEN_MAX_AGE_SECONDS = 300

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        actor = getattr(request, "user_dto", None)
        if actor is None:
            return redirect(reverse("mentores:list"))

        token = request.POST.get("token", "")
        if token:
            return self._apply_with_token(request, token)

        return self._render_confirm(request)

    # -- step 1 -----------------------------------------------------------
    def _render_confirm(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action", "")
        if action not in {self.ACTION_SELECTED, self.ACTION_ALL}:
            messages.error(request, "Acción no válida.")
            return redirect(reverse("mentores:list"))

        matriculas = request.POST.getlist("matriculas")
        if action == self.ACTION_SELECTED and not matriculas:
            messages.warning(
                request,
                "Selecciona al menos un mentor para desactivar.",
            )
            return redirect(reverse("mentores:list"))

        # Dedupe in the payload too so the confirm-page count and the
        # service's ``total_attempted`` agree.
        unique_matriculas = sorted(set(matriculas))
        token = signing.dumps(
            {"action": action, "matriculas": unique_matriculas},
            salt=self.SIGNING_SALT,
        )
        return render(
            request,
            self.template_name,
            {
                "action": action,
                "matriculas": unique_matriculas,
                "token": token,
            },
        )

    # -- step 2 -----------------------------------------------------------
    def _apply_with_token(self, request: HttpRequest, token: str) -> HttpResponse:
        try:
            payload = signing.loads(
                token,
                salt=self.SIGNING_SALT,
                max_age=self.TOKEN_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            messages.error(
                request,
                "La sesión de confirmación expiró o no es válida. Vuelve a intentar.",
            )
            return redirect(reverse("mentores:list"))

        action = payload.get("action")
        matriculas = payload.get("matriculas") or []
        if action not in {self.ACTION_SELECTED, self.ACTION_ALL}:
            messages.error(request, "Acción no válida.")
            return redirect(reverse("mentores:list"))

        actor = request.user_dto  # type: ignore[attr-defined]
        service = get_mentor_service()
        if action == self.ACTION_ALL:
            result = service.deactivate_all_active(actor)
        else:
            result = service.bulk_deactivate(matriculas, actor)

        self._flash_summary(request, result)
        return redirect(reverse("mentores:list"))

    @staticmethod
    def _flash_summary(request: HttpRequest, result: BulkDeactivateResult) -> None:
        if result.closed == 0 and result.already_inactive == 0:
            messages.info(request, "No hay mentores activos para desactivar.")
            return
        parts = [f"{result.closed} mentor(es) desactivado(s)"]
        if result.already_inactive:
            parts.append(f"{result.already_inactive} ya estaban inactivos")
        messages.success(request, "; ".join(parts) + ".")
