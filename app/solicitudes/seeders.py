"""Dev seed data for the solicitudes app.

Builds two representative tipos (with their fields) and two PDF plantillas,
each tipo wired to its plantilla, so the admin catalog and the PDF download
flow both work right after ``manage.py seed``.
"""
from __future__ import annotations

from typing import Any

from solicitudes.models import FieldDefinition, PlantillaSolicitud, TipoSolicitud
from solicitudes.tipos.constants import FieldType
from usuarios.constants import Role

# Run usuarios seeder first so admin sessions can be created against the
# seeded admin user before they touch this catalog.
DEPENDS_ON: list[str] = ["usuarios"]


SEEDED_SLUGS: list[str] = [
    "constancia-de-estudios",
    "solicitud-cambio-programa",
]


SEEDED_PLANTILLA_NAMES: list[str] = [
    "Constancia de Estudios",
    "Solicitud de Cambio de Programa",
]


_CONSTANCIA_HTML = """
<div class="header">
  <h1>Constancia de Estudios</h1>
  <p class="subtitle">Universidad Autónoma de Zacatecas</p>
</div>

<p>A quien corresponda:</p>

<p>
  Por medio de la presente se hace constar que
  <strong>{{ solicitante.nombre }}</strong>,
  con matrícula <strong>{{ solicitante.matricula }}</strong>,
  se encuentra inscrito(a) en el programa
  <strong>{{ valores.programa|default:solicitante.programa }}</strong>
  durante el semestre {{ solicitante.semestre|default:"en curso" }}.
</p>

<p>
  La presente se expide a solicitud del interesado para los fines que a su
  conveniencia procedan, en referencia al folio <strong>{{ solicitud.folio }}</strong>.
</p>

<p class="firma">{{ firma_lugar_fecha }}</p>

<p class="firma-rubrica">_____________________________<br>
Control Escolar</p>
""".strip()


_CONSTANCIA_CSS = """
@page { size: Letter; margin: 2.5cm 2cm 2.5cm 2cm; }
body {
  font-family: 'Liberation Serif', 'Times New Roman', serif;
  color: #212529;
  line-height: 1.55;
}
h1 { font-size: 18pt; margin: 0 0 .25rem; text-align: center; }
.header { border-bottom: 1px solid #adb5bd; padding-bottom: 1rem; margin-bottom: 2rem; }
.subtitle { text-align: center; color: #6c757d; margin: 0; font-size: 11pt; }
p { margin: 0 0 1rem; text-align: justify; }
.firma { margin-top: 3rem; text-align: right; }
.firma-rubrica { margin-top: 3.5rem; text-align: center; }
""".strip()


_CAMBIO_HTML = """
<div class="header">
  <h1>Solicitud de Cambio de Programa</h1>
  <p class="subtitle">Folio {{ solicitud.folio }}</p>
</div>

<p><strong>Solicitante:</strong> {{ solicitante.nombre }} ({{ solicitante.matricula }})</p>
<p><strong>Correo:</strong> {{ solicitante.email }}</p>

<table class="datos">
  <tr>
    <th>Programa actual</th>
    <td>{{ valores.programa_actual }}</td>
  </tr>
  <tr>
    <th>Programa solicitado</th>
    <td>{{ valores.programa_al_que_deseas_cambiar }}</td>
  </tr>
  <tr>
    <th>Motivo</th>
    <td>{{ valores.motivo_del_cambio }}</td>
  </tr>
</table>

<p class="firma">{{ firma_lugar_fecha }}</p>

<p class="firma-rubrica">_____________________________<br>
Firma del solicitante</p>
""".strip()


_CAMBIO_CSS = """
@page { size: Letter; margin: 2.5cm 2cm; }
body {
  font-family: 'Liberation Sans', 'Helvetica', sans-serif;
  color: #212529;
  line-height: 1.5;
  font-size: 11pt;
}
h1 { font-size: 16pt; margin: 0; }
.header { border-bottom: 2px solid #006837; padding-bottom: .75rem; margin-bottom: 1.5rem; }
.subtitle { color: #6c757d; margin: .25rem 0 0; }
table.datos { width: 100%; border-collapse: collapse; margin: 1.5rem 0; }
table.datos th {
  text-align: left;
  padding: .5rem .75rem;
  background: #f1f3f5;
  width: 35%;
  vertical-align: top;
}
table.datos td { padding: .5rem .75rem; border-bottom: 1px solid #dee2e6; }
.firma { margin-top: 2.5rem; }
.firma-rubrica { margin-top: 3rem; text-align: center; }
""".strip()


def run(*, fresh: bool) -> None:
    if fresh:
        TipoSolicitud.objects.filter(slug__in=SEEDED_SLUGS).delete()
        PlantillaSolicitud.objects.filter(nombre__in=SEEDED_PLANTILLA_NAMES).delete()

    plantilla_constancia, _ = PlantillaSolicitud.objects.update_or_create(
        nombre="Constancia de Estudios",
        defaults={
            "descripcion": "Plantilla oficial para la constancia de inscripción.",
            "html": _CONSTANCIA_HTML,
            "css": _CONSTANCIA_CSS,
            "activo": True,
        },
    )
    plantilla_cambio, _ = PlantillaSolicitud.objects.update_or_create(
        nombre="Solicitud de Cambio de Programa",
        defaults={
            "descripcion": "Plantilla del formato de cambio de programa.",
            "html": _CAMBIO_HTML,
            "css": _CAMBIO_CSS,
            "activo": True,
        },
    )

    constancia, _ = TipoSolicitud.objects.update_or_create(
        slug="constancia-de-estudios",
        defaults={
            "nombre": "Constancia de Estudios",
            "descripcion": "Documento que certifica la inscripción del alumno.",
            "responsible_role": Role.CONTROL_ESCOLAR.value,
            "creator_roles": [Role.ALUMNO.value],
            "requires_payment": False,
            "mentor_exempt": False,
            "plantilla": plantilla_constancia,
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
            "plantilla": plantilla_cambio,
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
