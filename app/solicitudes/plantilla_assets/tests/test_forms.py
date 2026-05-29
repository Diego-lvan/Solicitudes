"""Form-layer tests for AssetUploadForm."""
from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile

from solicitudes.plantilla_assets.constants import MAX_ASSET_BYTES
from solicitudes.plantilla_assets.forms import AssetUploadForm
from solicitudes.plantilla_assets.tests.factories import PNG_1X1


def test_valid_png_passes() -> None:
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    form = AssetUploadForm(data={"nombre": "Logo"}, files={"imagen": upload})
    assert form.is_valid(), form.errors


def test_bad_extension_rejected() -> None:
    upload = SimpleUploadedFile("logo.gif", PNG_1X1, content_type="image/png")
    form = AssetUploadForm(data={"nombre": "Logo"}, files={"imagen": upload})
    assert not form.is_valid()
    assert "imagen" in form.errors


def test_oversize_rejected() -> None:
    big = b"\x00" * (MAX_ASSET_BYTES + 1)
    upload = SimpleUploadedFile("logo.png", big, content_type="image/png")
    form = AssetUploadForm(data={"nombre": "Logo"}, files={"imagen": upload})
    assert not form.is_valid()
    assert "imagen" in form.errors


def test_bad_mime_rejected() -> None:
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="application/pdf")
    form = AssetUploadForm(data={"nombre": "Logo"}, files={"imagen": upload})
    assert not form.is_valid()
    assert "imagen" in form.errors


def test_whitespace_collapsing_to_short_name_rejected() -> None:
    # "  a " passes the field's min_length=2 (raw len) but `clean_nombre`
    # strips it to a single character → custom "muy corto" error.
    upload = SimpleUploadedFile("logo.png", PNG_1X1, content_type="image/png")
    form = AssetUploadForm(data={"nombre": "  a "}, files={"imagen": upload})
    assert not form.is_valid()
    assert "nombre" in form.errors
