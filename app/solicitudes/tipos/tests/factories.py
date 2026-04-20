"""Test factories for the tipos feature."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from model_bakery import baker

from solicitudes.models import FieldDefinition, TipoSolicitud
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.schemas import CreateFieldInput, CreateTipoInput
from usuarios.constants import Role


def make_tipo(**overrides: Any) -> TipoSolicitud:
    """Persisted ``TipoSolicitud`` with defaults; pass kwargs to override."""
    defaults: dict[str, Any] = {
        "slug": overrides.pop("slug", f"tipo-{uuid4().hex[:8]}"),
        "nombre": overrides.pop("nombre", "Constancia de Estudios"),
        "responsible_role": overrides.pop(
            "responsible_role", Role.CONTROL_ESCOLAR.value
        ),
        "creator_roles": overrides.pop("creator_roles", [Role.ALUMNO.value]),
    }
    defaults.update(overrides)
    tipo: TipoSolicitud = baker.make(TipoSolicitud, **defaults)
    return tipo


def make_field(tipo: TipoSolicitud, *, order: int = 0, **overrides: Any) -> FieldDefinition:
    """Persisted ``FieldDefinition`` attached to ``tipo``."""
    defaults: dict[str, Any] = {
        "label": overrides.pop("label", f"Campo {order}"),
        "field_type": overrides.pop("field_type", FieldType.TEXT.value),
        "order": order,
    }
    defaults.update(overrides)
    field: FieldDefinition = baker.make(FieldDefinition, tipo=tipo, **defaults)
    return field


def make_create_field_input(**overrides: Any) -> CreateFieldInput:
    """In-memory ``CreateFieldInput`` for service-layer tests."""
    fields: dict[str, Any] = {
        "label": "Nombre completo",
        "field_type": FieldType.TEXT,
        "required": True,
        "order": 0,
    }
    fields.update(overrides)
    return CreateFieldInput(**fields)


def make_create_tipo_input(**overrides: Any) -> CreateTipoInput:
    """In-memory ``CreateTipoInput`` for service-layer tests."""
    fields: dict[str, Any] = {
        "nombre": "Constancia de Estudios",
        "descripcion": "Documento que certifica inscripción.",
        "responsible_role": Role.CONTROL_ESCOLAR,
        "creator_roles": {Role.ALUMNO},
    }
    fields.update(overrides)
    return CreateTipoInput(**fields)
