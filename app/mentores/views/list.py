"""Admin list view for the mentor catalog."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.pagination import PageRequest
from mentores.dependencies import get_mentor_service
from mentores.permissions import AdminRequiredMixin


class MentorListView(AdminRequiredMixin, View):
    template_name = "mentores/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        # Default to active-only on first load. The template stamps a hidden
        # ``filtered=1`` sentinel so the view can distinguish a fresh load
        # (no params, default to active-only) from a deliberate submit where
        # the checkbox was left unchecked (show all).
        if request.GET.get("filtered") == "1":
            only_active = request.GET.get("only_active") == "1"
        else:
            only_active = True
        try:
            page_num = max(1, int(request.GET.get("page", "1")))
        except ValueError:
            page_num = 1
        page = get_mentor_service().list(
            only_active=only_active,
            page=PageRequest(page=page_num, page_size=20),
        )
        return render(
            request,
            self.template_name,
            {"page": page, "only_active": only_active},
        )
