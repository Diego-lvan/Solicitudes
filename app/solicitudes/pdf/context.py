"""Variable-resolution helper for PDF render context.

Builds the ``{solicitante, solicitud, valores, now, firma_lugar_fecha}``
mapping passed to the Django template engine when a plantilla is rendered.

Stays in its own module (not the service) so it's trivially unit-testable
without touching the WeasyPrint or DB layers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.utils.text import slugify

from solicitudes.lifecycle.schemas import SolicitudDetail
from usuarios.schemas import UserDTO

TZ_MX = ZoneInfo("America/Mexico_City")

_MESES_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def slug_for_label(label: str) -> str:
    """Slugify a field label deterministically.

    Plantillas reference values via ``{{ valores.<slug> }}``. Two fields with
    the same label after slugify collide on purpose — we treat their values
    as interchangeable for the template, which is the same convention the
    intake form preview uses.
    """
    slug = slugify(label)
    # Django's slugify uses '-'; templates can't reference attrs with hyphens,
    # so we normalize to underscores so the variable is reachable.
    return slug.replace("-", "_") or "campo"


def build_render_context(
    *,
    solicitud: SolicitudDetail,
    solicitante: UserDTO,
    now: datetime,
) -> dict[str, Any]:
    """Build the mapping that the plantilla's HTML is rendered with.

    Files (``FieldType.FILE``) are not embedded in the PDF; their value is
    rendered as the original filename for human-readable reference.
    """
    valores: dict[str, str] = {}
    raw_values: dict[str, Any] = dict(solicitud.valores or {})

    for field in solicitud.form_snapshot.fields:
        slug = slug_for_label(field.label)
        raw = raw_values.get(str(field.field_id))
        valores[slug] = _render_value(raw)

    now_local = now.astimezone(TZ_MX) if now.tzinfo else now
    return {
        "solicitante": {
            "matricula": solicitante.matricula,
            "nombre": solicitante.full_name,
            "email": solicitante.email,
            "programa": solicitante.programa,
            "semestre": solicitante.semestre,
            # Single-letter SIGA code: ``"H"`` (hombre) / ``"M"`` (mujer) /
            # ``""`` (desconocido). Plantillas pueden ramificar con
            # ``{% if solicitante.genero == "H" %}El{% elif … %}La{% else %}…``
            # sin que la app necesite saber nada de gramática.
            "genero": solicitante.gender,
        },
        "solicitud": {
            "folio": solicitud.folio,
            "estado": solicitud.estado.value,
            "tipo_nombre": solicitud.tipo.nombre,
            "created_at": solicitud.created_at,
            "updated_at": solicitud.updated_at,
        },
        "valores": valores,
        "now": now_local,
        "firma_lugar_fecha": _firma_lugar_fecha(now_local),
    }


def _render_value(raw: Any) -> str:
    """Render a raw form value as a string for the plantilla."""
    if raw is None:
        return ""
    if isinstance(raw, dict) and "filename" in raw:
        # FILE-type values are stored as {filename, ...}; only the filename
        # is shown in the PDF (the artifact itself is a separate download).
        return str(raw.get("filename", ""))
    if isinstance(raw, list):
        return ", ".join(str(item) for item in raw)
    return str(raw)


def _firma_lugar_fecha(now_local: datetime) -> str:
    mes = _MESES_ES[now_local.month - 1]
    return f"Zacatecas, Zac., a {now_local.day} de {mes} de {now_local.year}"


def build_synthetic_context(*, now: datetime) -> dict[str, object]:
    """Lorem-ipsum context for the admin's plantilla preview.

    Keys mirror :func:`build_render_context` so a plantilla that works for a
    real solicitud also renders against this synthetic context with no
    conditional logic.
    """
    now_local = now.astimezone(TZ_MX) if now.tzinfo else now
    return {
        "solicitante": {
            "matricula": "99999",
            "nombre": "Nombre Apellido Apellido",
            "email": "ejemplo@uaz.edu.mx",
            "programa": "Programa de Ejemplo",
            "semestre": 5,
            "genero": "H",  # admin preview: arbitrario; refleja un H típico.
        },
        "solicitud": {
            "folio": "SOL-AAAA-NNNNN",
            "estado": "FINALIZADA",
            "tipo_nombre": "Ejemplo de tipo",
            "created_at": now_local,
            "updated_at": now_local,
        },
        "valores": {},
        "now": now_local,
        "firma_lugar_fecha": _firma_lugar_fecha(now_local),
    }


def assemble_html(template_html: str, css: str) -> str:
    """Wrap rendered body HTML with ``<style>`` so WeasyPrint sees one document."""
    style = f"<style>{css}</style>" if css else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"{style}</head><body>{template_html}</body></html>"
    )
