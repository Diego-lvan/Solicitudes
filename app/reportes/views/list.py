"""Admin list view: paginated solicitud list with the same filter."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.pagination import PageRequest
from reportes.dependencies import get_report_service
from reportes.permissions import AdminRequiredMixin
from reportes.views._helpers import (
    filter_form_choices,
    get_filter_from_request,
    querystring_for,
)


class ReportListView(AdminRequiredMixin, View):
    template_name = "reportes/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        filter = get_filter_from_request(request)
        try:
            page_num = max(1, int(request.GET.get("page", "1")))
        except ValueError:
            page_num = 1
        page = get_report_service().list_paginated(
            filter=filter,
            page=PageRequest(page=page_num, page_size=25),
        )
        ctx = {
            "page": page,
            "filter": filter,
            "querystring": querystring_for(filter),
            **filter_form_choices(filter),
        }
        return render(request, self.template_name, ctx)
