"""Thin WeasyPrint wrapper.

Keeps the WeasyPrint import surface contained to this module.
"""
from __future__ import annotations


def render_pdf(
    html: str,
    *,
    base_url: str | None = None,
    pdf_identifier: bytes | None = None,
) -> bytes:
    """Render an HTML string into PDF bytes.

    ``pdf_identifier`` pins the PDF ``/ID`` array so that two renders of the
    same input under a frozen clock produce byte-identical output. Pass a
    value derived from a stable key (e.g. the solicitud folio) when
    determinism is required.
    """
    # Imported lazily so unit tests that don't touch PDFs don't pay the import cost.
    from weasyprint import HTML

    kwargs: dict[str, object] = {}
    if pdf_identifier is not None:
        kwargs["pdf_identifier"] = pdf_identifier
    pdf: bytes = HTML(string=html, base_url=base_url).write_pdf(**kwargs)
    return pdf
