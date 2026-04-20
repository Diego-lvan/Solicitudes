"""Dev seed data for the solicitudes app.

Builds two representative tipos with their fields so the admin catalog has
something to render right after ``manage.py seed``.
"""
from __future__ import annotations

from typing import Any

from solicitudes.models import FieldDefinition, TipoSolicitud
from solicitudes.tipos.constants import FieldType
from usuarios.constants import Role

# Run usuarios seeder first so admin sessions can be created against the
# seeded admin user before they touch this catalog.
DEPENDS_ON: list[str] = ["usuarios"]


SEEDED_SLUGS: list[str] = [
    "constancia-de-estudios",
    "solicitud-cambio-programa",
]


def run(*, fresh: bool) -> None:
    if fresh:
        TipoSolicitud.objects.filter(slug__in=SEEDED_SLUGS).delete()

    constancia, _ = TipoSolicitud.objects.update_or_create(
        slug="constancia-de-estudios",
        defaults={
            "nombre": "Constancia de Estudios",
            "descripcion": "Documento que certifica la inscripción del alumno.",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "requires_payment": False,
            "mentor_exempt": False,
            "activo": True,
        },
    )
    _replace_fields(
        constancia,
        [
            {
                "label": "Nombre completo",
                "field_type": FieldType.TEXT.value,
                "required": True,
                "order": 0,
            },
            {
                "label": "Programa",
                "field_type": FieldType.SELECT.value,
                "required": True,
                "order": 1,
                "options": ["ISW", "ISC", "Ing. en Comunicaciones y Electrónica"],
            },
            {
                "label": "Comprobante",
                "field_type": FieldType.FILE.value,
                "required": False,
                "order": 2,
                "accepted_extensions": [".pdf"],
                "max_size_mb": 5,
            },
        ],
    )

    cambio, _ = TipoSolicitud.objects.update_or_create(
        slug="solicitud-cambio-programa",
        defaults={
            "nombre": "Solicitud de Cambio de Programa",
            "descripcion": "Cambio académico hacia un programa distinto al de inscripción.",
            "responsible_role": Role.RESPONSABLE_PROGRAMA.value,
            "creator_roles": [Role.ALUMNO.value],
            "requires_payment": True,
            "mentor_exempt": True,
            "activo": True,
        },
    )
    _replace_fields(
        cambio,
        [
            {
                "label": "Programa actual",
                "field_type": FieldType.TEXT.value,
                "required": True,
                "order": 0,
            },
            {
                "label": "Programa al que deseas cambiar",
                "field_type": FieldType.TEXT.value,
                "required": True,
                "order": 1,
            },
            {
                "label": "Motivo del cambio",
                "field_type": FieldType.TEXTAREA.value,
                "required": True,
                "order": 2,
            },
        ],
    )


def _replace_fields(
    tipo: TipoSolicitud, defs: list[dict[str, Any]]
) -> None:
    """Idempotently replace the tipo's fieldset with ``defs`` (matched by ``order``)."""
    incoming_orders = {int(d["order"]) for d in defs}
    FieldDefinition.objects.filter(tipo=tipo).exclude(order__in=incoming_orders).delete()
    for d in defs:
        FieldDefinition.objects.update_or_create(
            tipo=tipo,
            order=int(d["order"]),
            defaults={
                "label": d["label"],
                "field_type": d["field_type"],
                "required": d.get("required", True),
                "options": d.get("options", []),
                "accepted_extensions": d.get("accepted_extensions", []),
                "max_size_mb": d.get("max_size_mb", 10),
                "max_chars": d.get("max_chars"),
                "placeholder": d.get("placeholder", ""),
                "help_text": d.get("help_text", ""),
            },
        )
