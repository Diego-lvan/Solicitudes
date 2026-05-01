"""Admin paginated list of users."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from usuarios.directory.dependencies import get_user_directory_service
from usuarios.directory.forms.filter_form import DirectoryFilterForm
from usuarios.directory.views._helpers import build_filter_querystring
from usuarios.permissions import AdminRequiredMixin


class DirectoryListView(AdminRequiredMixin, View):
    template_name = "usuarios/directory/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = DirectoryFilterForm(request.GET or None)
        form.is_valid()  # populate cleaned_data; never blocks
        filters = form.to_filters()
        page = get_user_directory_service().list(filters)
        ctx = {
            "page": page,
            "filters": filters,
            "form": form,
            "querystring": build_filter_querystring(filters),
        }
        return render(request, self.template_name, ctx)
