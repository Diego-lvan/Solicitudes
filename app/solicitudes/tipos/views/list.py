"""Admin list view for the tipos catalog."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from solicitudes.tipos.dependencies import get_tipo_service
from usuarios.constants import Role
from usuarios.permissions import AdminRequiredMixin


class TipoListView(AdminRequiredMixin, View):
    template_name = "solicitudes/admin/tipos/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        only_active_param = request.GET.get("only_active") == "1"
        responsible_role_value = request.GET.get("responsible_role") or ""
        responsible_role: Role | None = None
        if responsible_role_value:
            try:
                responsible_role = Role(responsible_role_value)
            except ValueError:
                responsible_role = None

        service = get_tipo_service()
        rows = service.list_for_admin(
            only_active=only_active_param,
            responsible_role=responsible_role,
        )

        return render(
            request,
            self.template_name,
            {
                "tipos": rows,
                "only_active": only_active_param,
                "responsible_role": responsible_role_value,
                "role_choices": Role,
            },
        )
