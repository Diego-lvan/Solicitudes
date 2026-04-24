"""Default TipoService implementation."""
from __future__ import annotations

import logging
from uuid import UUID

from django.utils import timezone

from _shared.exceptions import Unauthorized
from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.tipos.exceptions import TipoNotFound
from solicitudes.tipos.repositories.tipo.interface import TipoRepository
from solicitudes.tipos.schemas import (
    CreateTipoInput,
    TipoSolicitudDTO,
    TipoSolicitudRow,
    UpdateTipoInput,
)
from solicitudes.tipos.services.tipo_service.interface import TipoService
from usuarios.constants import Role

logger = logging.getLogger(__name__)


class DefaultTipoService(TipoService):
    """Owns the catalog's business rules; delegates persistence to a TipoRepository."""

    def __init__(self, tipo_repository: TipoRepository) -> None:
        self._repo = tipo_repository

    # ---- reads ----

    def list_for_admin(
        self,
        *,
        only_active: bool = False,
        responsible_role: Role | None = None,
    ) -> list[TipoSolicitudRow]:
        return self._repo.list(
            only_active=only_active, responsible_role=responsible_role
        )

    def list_for_creator(self, role: Role) -> list[TipoSolicitudRow]:
        # Only roles that *file* solicitudes (ALUMNO, DOCENTE) ever see this
        # list. For any other role, return empty rather than raising — the
        # caller may legitimately render an empty state.
        return self._repo.list(only_active=True, creator_role=role)

    def get_for_admin(self, tipo_id: UUID) -> TipoSolicitudDTO:
        return self._repo.get_by_id(tipo_id)

    def get_for_creator(self, slug: str, role: Role) -> TipoSolicitudDTO:
        tipo = self._repo.get_by_slug(slug)
        # Defense in depth — UI already filters to creator_roles tipos, but a
        # creator with a hand-typed URL must still be rejected.
        if not tipo.activo or role not in tipo.creator_roles:
            raise Unauthorized("No puedes crear este tipo de solicitud.")
        return tipo

    # ---- writes ----

    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO:
        # `CreateTipoInput` validators already enforce role allow-lists,
        # mentor_exempt normalization, field-count cap, and per-field
        # invariants. Service responsibility is logging + persistence.
        logger.info(
            "Creating tipo",
            extra={"nombre": input_dto.nombre, "fields": len(input_dto.fields)},
        )
        return self._repo.create(input_dto)

    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO:
        logger.info(
            "Updating tipo",
            extra={"tipo_id": str(input_dto.id), "fields": len(input_dto.fields)},
        )
        return self._repo.update(input_dto)

    def deactivate(self, tipo_id: UUID) -> None:
        # Idempotent — repository raises TipoNotFound if the row is missing.
        self._repo.deactivate(tipo_id)
        logger.info("Deactivated tipo", extra={"tipo_id": str(tipo_id)})

    # ---- snapshot ----

    def snapshot(self, tipo_id: UUID) -> FormSnapshot:
        tipo = self._repo.get_by_id(tipo_id)
        if not tipo.activo:
            raise TipoNotFound(f"id={tipo_id} (inactive)")
        return FormSnapshot(
            tipo_id=tipo.id,
            tipo_slug=tipo.slug,
            tipo_nombre=tipo.nombre,
            captured_at=timezone.now(),
            fields=[
                FieldSnapshot(
                    field_id=f.id,
                    label=f.label,
                    field_type=f.field_type,
                    required=f.required,
                    order=f.order,
                    options=list(f.options),
                    accepted_extensions=list(f.accepted_extensions),
                    max_size_mb=f.max_size_mb,
                    max_chars=f.max_chars,
                    placeholder=f.placeholder,
                    help_text=f.help_text,
                    source=f.source,
                )
                for f in tipo.fields
            ],
        )
