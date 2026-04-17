from __future__ import annotations

import pytest

pytest.importorskip("weasyprint")


def test_render_pdf_smoke() -> None:
    from _shared.pdf import render_pdf

    pdf = render_pdf("<html><body><h1>hola</h1></body></html>")
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100
