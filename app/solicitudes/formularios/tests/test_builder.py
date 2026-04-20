"""Tests for the formularios builder."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from solicitudes.formularios.builder import build_django_form, field_attr_name
from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.tipos.constants import FieldType


def _snap(**overrides: Any) -> FormSnapshot:
    base = FieldSnapshot(
        field_id=uuid4(), label="X", field_type=FieldType.TEXT, required=True, order=0
    )
    fields: list[FieldSnapshot] = list(overrides.pop("fields", [base]))
    return FormSnapshot(
        tipo_id=uuid4(),
        tipo_slug="t",
        tipo_nombre="T",
        captured_at=datetime.now(UTC),
        fields=fields,
    )


def test_text_field_renders_with_label_and_placeholder() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Nombre",
                field_type=FieldType.TEXT,
                required=True,
                order=0,
                placeholder="Tu nombre",
            ),
        ]
    )
    Form = build_django_form(snap)
    form = Form(data={field_attr_name(fid): "Ada"})
    assert form.is_valid()
    assert form.cleaned_data[field_attr_name(fid)] == "Ada"


def test_required_field_rejects_empty() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid, label="X", field_type=FieldType.TEXT, required=True, order=0
            ),
        ]
    )
    Form = build_django_form(snap)
    form = Form(data={field_attr_name(fid): ""})
    assert not form.is_valid()
    assert field_attr_name(fid) in form.errors


def test_select_accepts_only_declared_options() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Programa",
                field_type=FieldType.SELECT,
                required=True,
                order=0,
                options=["ISW", "ISC"],
            ),
        ]
    )
    Form = build_django_form(snap)
    assert Form(data={field_attr_name(fid): "ISW"}).is_valid()
    assert not Form(data={field_attr_name(fid): "OTHER"}).is_valid()


def test_number_field_coerces_decimal() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Monto",
                field_type=FieldType.NUMBER,
                required=True,
                order=0,
            ),
        ]
    )
    Form = build_django_form(snap)
    form = Form(data={field_attr_name(fid): "12.50"})
    assert form.is_valid()
    assert form.cleaned_data[field_attr_name(fid)] == Decimal("12.50")


def test_date_field_parses_iso() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Fecha",
                field_type=FieldType.DATE,
                required=True,
                order=0,
            ),
        ]
    )
    Form = build_django_form(snap)
    form = Form(data={field_attr_name(fid): "2026-04-25"})
    assert form.is_valid()
    assert form.cleaned_data[field_attr_name(fid)] == date(2026, 4, 25)


def test_file_field_rejects_disallowed_extension() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Comprobante",
                field_type=FieldType.FILE,
                required=True,
                order=0,
                accepted_extensions=[".pdf"],
                max_size_mb=1,
            ),
        ]
    )
    Form = build_django_form(snap)
    bad = SimpleUploadedFile("evil.exe", b"x", content_type="application/octet-stream")
    form = Form(data={}, files={field_attr_name(fid): bad})  # type: ignore[arg-type]
    assert not form.is_valid()
    assert field_attr_name(fid) in form.errors


def test_file_field_rejects_oversized() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Comprobante",
                field_type=FieldType.FILE,
                required=True,
                order=0,
                accepted_extensions=[".pdf"],
                max_size_mb=1,
            ),
        ]
    )
    Form = build_django_form(snap)
    oversized = SimpleUploadedFile(
        "big.pdf",
        BytesIO(b"\x00" * (2 * 1024 * 1024)).getvalue(),
        content_type="application/pdf",
    )
    form = Form(data={}, files={field_attr_name(fid): oversized})  # type: ignore[arg-type]
    assert not form.is_valid()


def test_file_field_accepts_valid_pdf() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Comprobante",
                field_type=FieldType.FILE,
                required=True,
                order=0,
                accepted_extensions=[".pdf"],
                max_size_mb=1,
            ),
        ]
    )
    Form = build_django_form(snap)
    good = SimpleUploadedFile("ok.pdf", b"hi", content_type="application/pdf")
    form = Form(data={}, files={field_attr_name(fid): good})  # type: ignore[arg-type]
    assert form.is_valid()


def test_field_order_matches_snapshot() -> None:
    ids = [uuid4() for _ in range(3)]
    snap = _snap(
        fields=[
            FieldSnapshot(field_id=ids[2], label="C", field_type=FieldType.TEXT, required=False, order=2),
            FieldSnapshot(field_id=ids[0], label="A", field_type=FieldType.TEXT, required=False, order=0),
            FieldSnapshot(field_id=ids[1], label="B", field_type=FieldType.TEXT, required=False, order=1),
        ]
    )
    Form = build_django_form(snap)
    form = Form()
    rendered = list(form)
    assert [f.label for f in rendered] == ["A", "B", "C"]


def test_to_values_dict_serializes_json_safe() -> None:
    text_id, num_id, date_id = uuid4(), uuid4(), uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(field_id=text_id, label="N", field_type=FieldType.TEXT, required=False, order=0),
            FieldSnapshot(field_id=num_id, label="M", field_type=FieldType.NUMBER, required=False, order=1),
            FieldSnapshot(field_id=date_id, label="F", field_type=FieldType.DATE, required=False, order=2),
        ]
    )
    Form = build_django_form(snap)
    form = Form(
        data={
            field_attr_name(text_id): "Ada",
            field_attr_name(num_id): "12.5",
            field_attr_name(date_id): "2026-04-25",
        }
    )
    assert form.is_valid()
    values = form.to_values_dict()  # type: ignore[attr-defined]
    assert values[str(text_id)] == "Ada"
    assert values[str(num_id)] == "12.5"
    assert values[str(date_id)] == "2026-04-25"


@pytest.mark.parametrize("ft", list(FieldType))
def test_every_field_type_is_buildable(ft: FieldType) -> None:
    fid = uuid4()
    extra: dict[str, object] = {}
    if ft is FieldType.SELECT:
        extra["options"] = ["A"]
    if ft is FieldType.FILE:
        extra["accepted_extensions"] = [".pdf"]
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="X",
                field_type=ft,
                required=False,
                order=0,
                **extra,
            )
        ]
    )
    Form = build_django_form(snap)
    assert Form is not None


def test_text_respects_max_chars_when_set() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="Apellido",
                field_type=FieldType.TEXT,
                required=True,
                order=0,
                max_chars=5,
            ),
        ]
    )
    Form = build_django_form(snap)
    too_long = Form(data={field_attr_name(fid): "Mendiola"})
    assert not too_long.is_valid()
    assert "max_chars" not in too_long.errors  # uses Django's max_length error
    fits = Form(data={field_attr_name(fid): "Lopez"})
    assert fits.is_valid()


def test_text_falls_back_to_default_max_when_max_chars_is_none() -> None:
    fid = uuid4()
    snap = _snap(
        fields=[
            FieldSnapshot(
                field_id=fid,
                label="L",
                field_type=FieldType.TEXT,
                required=True,
                order=0,
                max_chars=None,
            ),
        ]
    )
    Form = build_django_form(snap)
    # Default cap is 200 chars; 199 should fit, 201 should not.
    assert Form(data={field_attr_name(fid): "x" * 199}).is_valid()
    assert not Form(data={field_attr_name(fid): "x" * 201}).is_valid()
