"""Test factories for solicitud lifecycle entities."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from django.utils.text import slugify
from model_bakery import baker

from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.models import HistorialEstado, Solicitud, TipoSolicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.tests.factories import make_user


def make_form_snapshot(tipo: TipoSolicitud) -> dict[str, Any]:
    """Empty form snapshot suited for solicitudes that do not need fields."""
    return FormSnapshot(
        tipo_id=tipo.id,
        tipo_slug=tipo.slug,
        tipo_nombre=tipo.nombre,
        captured_at=datetime.now(tz=UTC),
        fields=[],
    ).model_dump(mode="json")


def make_solicitud(
    *,
    folio: str | None = None,
    tipo: TipoSolicitud | None = None,
    solicitante: Any = None,
    estado: Estado = Estado.CREADA,
    requiere_pago: bool = False,
    pago_exento: bool = False,
    valores: dict[str, Any] | None = None,
    form_snapshot: dict[str, Any] | None = None,
) -> Solicitud:
    """Persisted Solicitud row with defaults for tests."""
    tipo = tipo or make_tipo(slug=slugify(f"tipo-{uuid4().hex[:8]}"))
    if solicitante is None:
        suffix = uuid4().hex[:8]
        solicitante = make_user(
            matricula=f"M-{suffix}",
            email=f"u-{suffix}@uaz.edu.mx",
            role=Role.ALUMNO.value,
        )
    folio = folio or f"SOL-2026-{uuid4().int % 100_000:05d}"
    return baker.make(
        Solicitud,
        folio=folio,
        tipo=tipo,
        solicitante=solicitante,
        estado=estado.value,
        form_snapshot=form_snapshot or make_form_snapshot(tipo),
        valores=valores or {},
        requiere_pago=requiere_pago,
        pago_exento=pago_exento,
    )


def make_historial(
    solicitud: Solicitud,
    *,
    estado_anterior: Estado | None = None,
    estado_nuevo: Estado = Estado.CREADA,
    actor: Any = None,
    actor_role: Role = Role.ALUMNO,
    observaciones: str = "",
) -> HistorialEstado:
    actor = actor or solicitud.solicitante
    return baker.make(
        HistorialEstado,
        solicitud=solicitud,
        estado_anterior=estado_anterior.value if estado_anterior else None,
        estado_nuevo=estado_nuevo.value,
        actor=actor,
        actor_role=actor_role.value,
        observaciones=observaciones,
    )
