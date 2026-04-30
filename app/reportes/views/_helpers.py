"""Shared helpers for reportes views."""
from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpRequest

from reportes.forms.report_filter_form import parse_report_filter
from reportes.schemas import ReportFilter
from solicitudes.lifecycle.constants import Estado
from solicitudes.tipos.dependencies import get_tipo_service
from usuarios.constants import Role

# Responsible-role choices in the order they should appear in the dropdown.
_RESPONSIBLE_ROLES = (Role.CONTROL_ESCOLAR, Role.RESPONSABLE_PROGRAMA, Role.DOCENTE)
_ROLE_DISPLAY: dict[Role, str] = {
    Role.CONTROL_ESCOLAR: "Control Escolar",
    Role.RESPONSABLE_PROGRAMA: "Responsable de Programa",
    Role.DOCENTE: "Docente",
}


def get_filter_from_request(request: HttpRequest) -> ReportFilter:
    return parse_report_filter(request.GET)


def querystring_for(filter: ReportFilter) -> str:
    """Encode a ReportFilter back into a querystring (skipping empty values)."""
    pairs: list[tuple[str, str]] = []
    if filter.estado is not None:
        pairs.append(("estado", filter.estado.value))
    if filter.tipo_id is not None:
        pairs.append(("tipo_id", str(filter.tipo_id)))
    if filter.responsible_role is not None:
        pairs.append(("responsible_role", filter.responsible_role.value))
    if filter.created_from is not None:
        pairs.append(("created_from", filter.created_from.isoformat()))
    if filter.created_to is not None:
        pairs.append(("created_to", filter.created_to.isoformat()))
    return urlencode(pairs)


def filter_form_choices(filter: ReportFilter) -> dict[str, object]:
    """Choice tuples for the filter form template, plus the active values
    pre-stringified so the template can compare them against option values
    (Django template equality requires the same type).
    """
    estado_choices = [(e.value, e.display_name) for e in Estado]
    role_choices = [(r.value, _ROLE_DISPLAY[r]) for r in _RESPONSIBLE_ROLES]
    tipos = get_tipo_service().list_for_admin(only_active=False)
    tipo_choices = [(str(t.id), t.nombre) for t in tipos]
    return {
        "estado_choices": estado_choices,
        "role_choices": role_choices,
        "tipo_choices": tipo_choices,
        # Pre-stringified active values for `selected` comparisons.
        "selected_estado": filter.estado.value if filter.estado else "",
        "selected_tipo_id": str(filter.tipo_id) if filter.tipo_id else "",
        "selected_role": (
            filter.responsible_role.value if filter.responsible_role else ""
        ),
    }
