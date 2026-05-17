"""HTTP-status sentinels for respuesta exceptions."""
from __future__ import annotations

from solicitudes.respuesta.exceptions import (
    ArchivoRespuestaNotFound,
    EmptyRespuestaBatch,
    InvalidStateForRespuesta,
    ResponseFileExtensionNotAllowed,
    ResponseFileTooLarge,
    RespuestaNotFound,
    TooManyFilesInBatch,
)


def test_not_found_maps_to_404() -> None:
    assert RespuestaNotFound().http_status == 404
    assert ArchivoRespuestaNotFound().http_status == 404


def test_invalid_state_maps_to_409() -> None:
    assert InvalidStateForRespuesta().http_status == 409


def test_too_many_files_maps_to_422_with_field_errors() -> None:
    exc = TooManyFilesInBatch(count=11, max_count=10)
    assert exc.http_status == 422
    assert "archivos" in exc.field_errors


def test_empty_batch_maps_to_422_with_all_field() -> None:
    exc = EmptyRespuestaBatch()
    assert exc.http_status == 422
    assert "__all__" in exc.field_errors


def test_response_file_too_large_carries_sizes() -> None:
    exc = ResponseFileTooLarge(size_bytes=11_000_000, max_bytes=10 * 1024 * 1024)
    assert exc.http_status == 422
    assert exc.size_bytes == 11_000_000


def test_response_file_extension_not_allowed_carries_extension() -> None:
    exc = ResponseFileExtensionNotAllowed(extension=".exe", allowed=(".pdf",))
    assert exc.http_status == 422
    assert exc.extension == ".exe"
