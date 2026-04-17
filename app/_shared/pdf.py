"""Thin WeasyPrint wrapper.

Keeps the WeasyPrint import surface contained to this module.
"""
from __future__ import annotations


def render_pdf(html: str, *, base_url: str | None = None) -> bytes:
    """Render an HTML string into PDF bytes."""
    # Imported lazily so unit tests that don't touch PDFs don't pay the import cost.
    from weasyprint import HTML

    pdf: bytes = HTML(string=html, base_url=base_url).write_pdf()
    return pdf
