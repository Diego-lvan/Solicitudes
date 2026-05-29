"""Form + model __str__ tests for the mentores feature."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from mentores.forms import CsvImportForm
from mentores.forms.csv_import_form import MAX_BYTES
from mentores.tests.factories import make_admin_user, make_mentor_periodo


def test_csv_import_form_rejects_oversize_file() -> None:
    big = SimpleUploadedFile(
        "big.csv", b"matricula\n" + b"1" * (MAX_BYTES + 1), content_type="text/csv"
    )
    form = CsvImportForm(data={}, files={"archivo": big})
    assert not form.is_valid()
    assert "archivo" in form.errors


def test_csv_import_form_accepts_small_file() -> None:
    small = SimpleUploadedFile(
        "ok.csv", b"matricula\n11111111\n", content_type="text/csv"
    )
    form = CsvImportForm(data={}, files={"archivo": small})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["archivo"].startswith(b"matricula")


@pytest.mark.django_db
def test_mentor_periodo_str_active_and_inactive() -> None:
    admin = make_admin_user()
    active = make_mentor_periodo(matricula="11111111", creado_por=admin)
    assert "[activo]" in str(active)
    assert "11111111" in str(active)
    inactive = make_mentor_periodo(
        matricula="22222222",
        creado_por=admin,
        fecha_baja=timezone.now() - timedelta(days=1),
    )
    assert "[inactivo]" in str(inactive)
