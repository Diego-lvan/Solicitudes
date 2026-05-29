"""Form-level validation for the response upload form."""
from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

from solicitudes.respuesta.forms.respuesta_upload_form import RespuestaUploadForm


class _MultiValueFiles(QueryDict):
    """QueryDict initialised mutable + multi-valued, matching what
    ``request.FILES`` looks like under a multi-file <input>."""

    def __init__(self) -> None:
        super().__init__("", mutable=True)


def _files(*items: SimpleUploadedFile) -> _MultiValueFiles:
    q = _MultiValueFiles()
    for f in items:
        q.appendlist("archivos", f)
    return q


def test_empty_submission_rejected() -> None:
    form = RespuestaUploadForm(data={"comentario": ""}, files=_files())
    assert not form.is_valid()
    assert any(
        "al menos un archivo" in str(err).lower()
        or "al menos" in str(err).lower()
        for err in form.errors.get("__all__", [])
    )


def test_comment_only_accepted() -> None:
    form = RespuestaUploadForm(data={"comentario": "Listo"}, files=_files())
    assert form.is_valid(), form.errors
    assert form.cleaned_data["comentario"] == "Listo"
    assert form.cleaned_data["archivos_list"] == []


def test_single_file_accepted() -> None:
    f = SimpleUploadedFile("a.pdf", b"data", content_type="application/pdf")
    form = RespuestaUploadForm(data={"comentario": ""}, files=_files(f))
    assert form.is_valid(), form.errors
    assert len(form.cleaned_data["archivos_list"]) == 1


def test_eleven_files_rejected() -> None:
    files = _files(
        *[
            SimpleUploadedFile(f"a{i}.pdf", b"x", content_type="application/pdf")
            for i in range(11)
        ]
    )
    form = RespuestaUploadForm(data={"comentario": ""}, files=files)
    assert not form.is_valid()
    assert any(
        "10" in str(err) for err in form.errors.get("__all__", [])
    )


def test_files_plus_comment_accepted() -> None:
    f = SimpleUploadedFile("a.pdf", b"data", content_type="application/pdf")
    form = RespuestaUploadForm(data={"comentario": "Hola"}, files=_files(f))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["comentario"] == "Hola"
    assert len(form.cleaned_data["archivos_list"]) == 1


def test_multiple_file_field_to_python_handles_empty_and_single() -> None:
    from solicitudes.respuesta.forms.respuesta_upload_form import (
        _MultipleFileField,
    )

    field = _MultipleFileField(required=False)
    # Empty / None inputs collapse to None.
    assert field.to_python(None) is None
    assert field.to_python("") is None
    # A single (non-list) UploadedFile is wrapped into a one-item list.
    one = SimpleUploadedFile("a.pdf", b"data", content_type="application/pdf")
    out = field.to_python(one)
    assert isinstance(out, list)
    assert len(out) == 1
