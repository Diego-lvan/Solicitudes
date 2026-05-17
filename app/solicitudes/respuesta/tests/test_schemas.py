"""Pydantic DTO validation for respuesta inputs."""
from __future__ import annotations

import pytest

from solicitudes.respuesta.schemas import CreateRespuestaInput, UploadedFile


def _file(name: str = "x.pdf", size: int = 100) -> UploadedFile:
    return UploadedFile(
        nombre_original=name,
        content_type="application/pdf",
        size_bytes=size,
        content=b"x" * size,
    )


def test_files_only_is_valid() -> None:
    dto = CreateRespuestaInput(
        folio="SOL-2026-00001",
        actor_matricula="P1",
        actor_role="CONTROL_ESCOLAR",
        archivos=[_file()],
    )
    assert len(dto.archivos) == 1


def test_comment_only_is_valid() -> None:
    dto = CreateRespuestaInput(
        folio="SOL-2026-00001",
        actor_matricula="P1",
        actor_role="CONTROL_ESCOLAR",
        comentario="Listo",
    )
    assert dto.comentario == "Listo"


def test_both_files_and_comment_is_valid() -> None:
    dto = CreateRespuestaInput(
        folio="SOL-2026-00001",
        actor_matricula="P1",
        actor_role="CONTROL_ESCOLAR",
        comentario="Adjunto constancia firmada",
        archivos=[_file()],
    )
    assert dto.comentario == "Adjunto constancia firmada"


def test_empty_batch_rejected() -> None:
    with pytest.raises(ValueError):
        CreateRespuestaInput(
            folio="SOL-2026-00001",
            actor_matricula="P1",
            actor_role="CONTROL_ESCOLAR",
        )


def test_whitespace_only_comment_treated_as_empty() -> None:
    with pytest.raises(ValueError):
        CreateRespuestaInput(
            folio="SOL-2026-00001",
            actor_matricula="P1",
            actor_role="CONTROL_ESCOLAR",
            comentario="   \n  ",
        )


def test_more_than_max_files_rejected() -> None:
    with pytest.raises(ValueError):
        CreateRespuestaInput(
            folio="SOL-2026-00001",
            actor_matricula="P1",
            actor_role="CONTROL_ESCOLAR",
            archivos=[_file(name=f"{i}.pdf") for i in range(11)],
        )


def test_comment_over_2000_chars_rejected() -> None:
    with pytest.raises(ValueError):
        CreateRespuestaInput(
            folio="SOL-2026-00001",
            actor_matricula="P1",
            actor_role="CONTROL_ESCOLAR",
            comentario="x" * 2001,
        )
