"""Pydantic DTOs for the tipos feature."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from solicitudes.tipos.constants import (
    ALLOWED_CREATOR_ROLES,
    ALLOWED_RESPONSIBLE_ROLES,
    MAX_FIELDS_PER_TIPO,
    FieldType,
)
from usuarios.constants import Role


class FieldDefinitionDTO(BaseModel):
    """Persisted field definition, returned by the repository."""

    model_config = {"frozen": True}

    id: UUID
    label: str
    field_type: FieldType
    required: bool
    order: int
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = 10
    max_chars: int | None = None
    placeholder: str = ""
    help_text: str = ""


class TipoSolicitudDTO(BaseModel):
    """Full hydrated tipo with its ordered fields."""

    model_config = {"frozen": True}

    id: UUID
    slug: str
    nombre: str
    descripcion: str
    responsible_role: Role
    creator_roles: set[Role]
    requires_payment: bool
    mentor_exempt: bool
    plantilla_id: UUID | None
    activo: bool
    fields: list[FieldDefinitionDTO]


class TipoSolicitudRow(BaseModel):
    """Trimmed DTO for list views — no fields, no plantilla."""

    model_config = {"frozen": True}

    id: UUID
    slug: str
    nombre: str
    responsible_role: Role
    creator_roles: set[Role]
    requires_payment: bool
    activo: bool


class CreateFieldInput(BaseModel):
    """One field row inside a CreateTipoInput / UpdateTipoInput."""

    # `id` is None when adding a brand-new field; populated when the admin is
    # editing an existing field (so the repo can update in place rather than
    # delete-and-recreate, which would invalidate snapshots that point at the
    # field by id).
    id: UUID | None = None
    label: str = Field(min_length=1, max_length=120)
    field_type: FieldType
    required: bool = True
    order: int = Field(ge=0)
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = Field(default=10, ge=1, le=50)
    max_chars: int | None = Field(default=None, ge=1, le=2000)
    placeholder: str = ""
    help_text: str = ""

    # Validator order matters here: shape-of-value checks (options, extensions)
    # run before the per-type-only flags (max_chars). When the admin posts a
    # SELECT field that is *both* missing options *and* carries a stale
    # max_chars value, the user-actionable "missing options" error surfaces
    # first instead of the noisier "max_chars only applies to TEXT…" — the
    # latter is auto-fixable by the form-layer normalization once the type
    # is corrected.

    @model_validator(mode="after")
    def _check_options(self) -> CreateFieldInput:
        if self.field_type is FieldType.SELECT and not self.options:
            raise ValueError("SELECT fields must define at least one option")
        if self.field_type is not FieldType.SELECT and self.options:
            raise ValueError("only SELECT fields may use options")
        return self

    @model_validator(mode="after")
    def _check_extensions(self) -> CreateFieldInput:
        if self.field_type is FieldType.FILE and not self.accepted_extensions:
            raise ValueError("FILE fields must declare accepted_extensions")
        if self.field_type is not FieldType.FILE and self.accepted_extensions:
            raise ValueError("only FILE fields may declare accepted_extensions")
        return self

    @model_validator(mode="after")
    def _check_max_chars_scope(self) -> CreateFieldInput:
        if self.max_chars is not None and self.field_type not in (
            FieldType.TEXT,
            FieldType.TEXTAREA,
        ):
            raise ValueError(
                "max_chars only applies to TEXT and TEXTAREA fields"
            )
        return self


class CreateTipoInput(BaseModel):
    """Input to TipoService.create."""

    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str = ""
    responsible_role: Role
    creator_roles: set[Role] = Field(min_length=1)
    requires_payment: bool = False
    mentor_exempt: bool = False
    plantilla_id: UUID | None = None
    fields: list[CreateFieldInput] = []

    @model_validator(mode="after")
    def _check_creator_roles(self) -> CreateTipoInput:
        allowed = {Role(r) for r in ALLOWED_CREATOR_ROLES}
        if not self.creator_roles.issubset(allowed):
            raise ValueError(
                "creator_roles only supports ALUMNO and DOCENTE"
            )
        return self

    @model_validator(mode="after")
    def _check_responsible_role(self) -> CreateTipoInput:
        allowed = {Role(r) for r in ALLOWED_RESPONSIBLE_ROLES}
        if self.responsible_role not in allowed:
            raise ValueError(
                "responsible_role must be CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA, or DOCENTE"
            )
        return self

    @model_validator(mode="after")
    def _normalize_mentor_exempt(self) -> CreateTipoInput:
        # Auto-clear: mentor_exempt is only meaningful when requires_payment.
        # Explicit clearing here means UI / admin edit toggling off
        # `requires_payment` cannot leave a stale flag behind.
        if self.mentor_exempt and not self.requires_payment:
            self.mentor_exempt = False
        return self

    @model_validator(mode="after")
    def _check_field_count(self) -> CreateTipoInput:
        if len(self.fields) > MAX_FIELDS_PER_TIPO:
            raise ValueError(
                f"a tipo cannot have more than {MAX_FIELDS_PER_TIPO} fields"
            )
        return self

    @model_validator(mode="after")
    def _check_field_orders_unique(self) -> CreateTipoInput:
        orders = [f.order for f in self.fields]
        if len(set(orders)) != len(orders):
            raise ValueError("field `order` values must be unique within a tipo")
        return self


class UpdateTipoInput(CreateTipoInput):
    """Input to TipoService.update — same shape plus the target id."""

    id: UUID
