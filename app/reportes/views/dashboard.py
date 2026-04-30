"""Admin dashboard view: aggregate counts + filter form."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from reportes.dependencies import get_report_service
from reportes.permissions import AdminRequiredMixin
from reportes.views._helpers import (
    filter_form_choices,
    get_filter_from_request,
    querystring_for,
)


class DashboardView(AdminRequiredMixin, View):
    template_name = "reportes/dashboard.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        filter = get_filter_from_request(request)
        dashboard = get_report_service().dashboard(filter=filter)
        ctx = {
            "dashboard": dashboard,
            "filter": filter,
            "querystring": querystring_for(filter),
            **filter_form_choices(filter),
        }
        return render(request, self.template_name, ctx)
