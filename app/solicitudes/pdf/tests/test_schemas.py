"""Pydantic schema validation tests for the pdf feature."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from solicitudes.pdf.schemas import (
    CreatePlantillaInput,
    PdfRenderResult,
    PlantillaDTO,
    PlantillaRow,
    UpdatePlantillaInput,
)


class TestCreatePlantillaInput:
    def test_minimal_valid_payload(self) -> None:
        inp = CreatePlantillaInput(nombre="Constancia", html="<p>Hola</p>")
        assert inp.nombre == "Constancia"
        assert inp.descripcion == ""
        assert inp.css == ""
        assert inp.activo is True

    def test_nombre_min_length_enforced(self) -> None:
        with pytest.raises(ValidationError):
            CreatePlantillaInput(nombre="ab", html="<p>x</p>")

    def test_nombre_max_length_enforced(self) -> None:
        with pytest.raises(ValidationError):
            CreatePlantillaInput(nombre="x" * 121, html="<p>x</p>")

    def test_html_required_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            CreatePlantillaInput(nombre="ok name", html="")


class TestUpdatePlantillaInput:
    def test_requires_id(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePlantillaInput(nombre="ok name", html="<p>x</p>")  # type: ignore[call-arg]

    def test_with_id(self) -> None:
        pid = uuid4()
        inp = UpdatePlantillaInput(id=pid, nombre="ok name", html="<p>x</p>")
        assert inp.id == pid


class TestPlantillaDTO:
    def test_frozen(self) -> None:
        dto = PlantillaDTO(
            id=uuid4(),
            nombre="X",
            descripcion="",
            html="<p/>",
            css="",
            activo=True,
        )
        with pytest.raises(ValidationError):
            dto.nombre = "Y"  # type: ignore[misc]


class TestPlantillaRow:
    def test_omits_blobs(self) -> None:
        row = PlantillaRow(id=uuid4(), nombre="X", descripcion="", activo=True)
        assert "html" not in row.model_dump()
        assert "css" not in row.model_dump()


class TestPdfRenderResult:
    def test_holds_bytes_and_metadata(self) -> None:
        res = PdfRenderResult(
            folio="SOL-2026-00001",
            bytes_=b"%PDF-1.7\n...",
            suggested_filename="constancia-SOL-2026-00001.pdf",
        )
        assert res.bytes_.startswith(b"%PDF")
        assert res.suggested_filename.endswith(".pdf")
