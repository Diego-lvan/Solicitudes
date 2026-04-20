"""In-memory fakes for tipos tests."""
from __future__ import annotations

from uuid import UUID, uuid4

from django.utils.text import slugify

from solicitudes.tipos.exceptions import TipoNotFound, TipoSlugConflict
from solicitudes.tipos.repositories.tipo.interface import TipoRepository
from solicitudes.tipos.schemas import (
    CreateTipoInput,
    FieldDefinitionDTO,
    TipoSolicitudDTO,
    TipoSolicitudRow,
    UpdateTipoInput,
)
from usuarios.constants import Role


class InMemoryTipoRepository(TipoRepository):
    """Hand-rolled fake. Stores DTOs directly so the service stays decoupled."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, TipoSolicitudDTO] = {}
        # Track tipos that "have solicitudes" for has_solicitudes() — tests
        # set this explicitly.
        self.tipos_with_solicitudes: set[UUID] = set()

    # ---- helper for tests ----

    def seed(self, dto: TipoSolicitudDTO) -> TipoSolicitudDTO:
        self._by_id[dto.id] = dto
        return dto

    # ---- TipoRepository ----

    def get_by_id(self, tipo_id: UUID) -> TipoSolicitudDTO:
        if tipo_id not in self._by_id:
            raise TipoNotFound(f"id={tipo_id}")
        return self._by_id[tipo_id]

    def get_by_slug(self, slug: str) -> TipoSolicitudDTO:
        for dto in self._by_id.values():
            if dto.slug == slug:
                return dto
        raise TipoNotFound(f"slug={slug}")

    def list(
        self,
        *,
        only_active: bool = False,
        creator_role: Role | None = None,
        responsible_role: Role | None = None,
    ) -> list[TipoSolicitudRow]:
        rows: list[TipoSolicitudRow] = []
        for dto in self._by_id.values():
            if only_active and not dto.activo:
                continue
            if responsible_role is not None and dto.responsible_role != responsible_role:
                continue
            if creator_role is not None and creator_role not in dto.creator_roles:
                continue
            rows.append(
                TipoSolicitudRow(
                    id=dto.id,
                    slug=dto.slug,
                    nombre=dto.nombre,
                    responsible_role=dto.responsible_role,
                    creator_roles=dto.creator_roles,
                    requires_payment=dto.requires_payment,
                    activo=dto.activo,
                )
            )
        rows.sort(key=lambda r: r.nombre)
        return rows

    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO:
        slug = slugify(input_dto.nombre) or "tipo"
        if any(d.slug == slug for d in self._by_id.values()):
            raise TipoSlugConflict(f"slug={slug}")
        new_id = uuid4()
        dto = TipoSolicitudDTO(
            id=new_id,
            slug=slug,
            nombre=input_dto.nombre,
            descripcion=input_dto.descripcion,
            responsible_role=input_dto.responsible_role,
            creator_roles=set(input_dto.creator_roles),
            requires_payment=input_dto.requires_payment,
            mentor_exempt=input_dto.mentor_exempt,
            plantilla_id=input_dto.plantilla_id,
            activo=True,
            fields=[
                FieldDefinitionDTO(
                    id=f.id or uuid4(),
                    label=f.label,
                    field_type=f.field_type,
                    required=f.required,
                    order=f.order,
                    options=list(f.options),
                    accepted_extensions=list(f.accepted_extensions),
                    max_size_mb=f.max_size_mb,
                    placeholder=f.placeholder,
                    help_text=f.help_text,
                )
                for f in input_dto.fields
            ],
        )
        self._by_id[new_id] = dto
        return dto

    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO:
        if input_dto.id not in self._by_id:
            raise TipoNotFound(f"id={input_dto.id}")
        existing = self._by_id[input_dto.id]
        existing_field_ids = {f.id for f in existing.fields}
        new_fields = [
            FieldDefinitionDTO(
                id=f.id if f.id and f.id in existing_field_ids else uuid4(),
                label=f.label,
                field_type=f.field_type,
                required=f.required,
                order=f.order,
                options=list(f.options),
                accepted_extensions=list(f.accepted_extensions),
                max_size_mb=f.max_size_mb,
                placeholder=f.placeholder,
                help_text=f.help_text,
            )
            for f in input_dto.fields
        ]
        new_fields.sort(key=lambda f: f.order)
        dto = TipoSolicitudDTO(
            id=existing.id,
            slug=existing.slug,  # slug never changes via update.
            nombre=input_dto.nombre,
            descripcion=input_dto.descripcion,
            responsible_role=input_dto.responsible_role,
            creator_roles=set(input_dto.creator_roles),
            requires_payment=input_dto.requires_payment,
            mentor_exempt=input_dto.mentor_exempt,
            plantilla_id=input_dto.plantilla_id,
            activo=existing.activo,
            fields=new_fields,
        )
        self._by_id[existing.id] = dto
        return dto

    def deactivate(self, tipo_id: UUID) -> None:
        if tipo_id not in self._by_id:
            raise TipoNotFound(f"id={tipo_id}")
        old = self._by_id[tipo_id]
        self._by_id[tipo_id] = old.model_copy(update={"activo": False})

    def has_solicitudes(self, tipo_id: UUID) -> bool:
        return tipo_id in self.tipos_with_solicitudes
