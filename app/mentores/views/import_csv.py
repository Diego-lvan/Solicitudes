"""CSV bulk-import view (admin)."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from _shared.exceptions import AppError
from mentores.dependencies import get_mentor_csv_importer
from mentores.forms import CsvImportForm
from mentores.permissions import AdminRequiredMixin


class ImportCsvView(AdminRequiredMixin, View):
    template_name = "mentores/import_csv.html"
    result_template_name = "mentores/import_result.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": CsvImportForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = CsvImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        actor = getattr(request, "user_dto", None)
        if actor is None:
            return render(request, self.template_name, {"form": form}, status=403)

        importer = get_mentor_csv_importer()
        try:
            result = importer.import_csv(form.cleaned_data["archivo"], actor=actor)
        except AppError as exc:
            form.add_error("archivo", exc.user_message)
            return render(
                request, self.template_name, {"form": form}, status=exc.http_status
            )

        return render(request, self.result_template_name, {"result": result})
