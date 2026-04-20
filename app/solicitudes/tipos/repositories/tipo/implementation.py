"""ORM-backed implementation of :class:`TipoRepository`."""
from __future__ import annotations

from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils.text import slugify

from solicitudes.models import FieldDefinition, TipoSolicitud
from solicitudes.tipos.constants import MAX_FIELDS_PER_TIPO
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


class OrmTipoRepository(TipoRepository):
    """Django ORM implementation. Owns all access to TipoSolicitud + FieldDefinition."""

    def get_by_id(self, tipo_id: UUID) -> TipoSolicitudDTO:
        try:
            tipo = (
                TipoSolicitud.objects.prefetch_related("fields").get(pk=tipo_id)
            )
        except TipoSolicitud.DoesNotExist as exc:
            raise TipoNotFound(f"id={tipo_id}") from exc
        return self._to_dto(tipo)

    def get_by_slug(self, slug: str) -> TipoSolicitudDTO:
        try:
            tipo = TipoSolicitud.objects.prefetch_related("fields").get(slug=slug)
        except TipoSolicitud.DoesNotExist as exc:
            raise TipoNotFound(f"slug={slug}") from exc
        return self._to_dto(tipo)

    def list(
        self,
        *,
        only_active: bool = False,
        creator_role: Role | None = None,
        responsible_role: Role | None = None,
    ) -> list[TipoSolicitudRow]:
        qs = TipoSolicitud.objects.all()
        if only_active:
            qs = qs.filter(activo=True)
        if responsible_role is not None:
            qs = qs.filter(responsible_role=responsible_role.value)
        if creator_role is not None:
            # JSONField containment — Postgres uses `?`; SQLite (dev) needs the
            # `__contains` lookup that Django translates per backend.
            qs = qs.filter(creator_roles__contains=[creator_role.value])
        return [self._to_row(t) for t in qs]

    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO:
        slug = self._build_unique_slug(input_dto.nombre)
        try:
            with transaction.atomic():
                tipo = TipoSolicitud.objects.create(
                    slug=slug,
                    nombre=input_dto.nombre,
                    descripcion=input_dto.descripcion,
                    responsible_role=input_dto.responsible_role.value,
                    creator_roles=sorted(r.value for r in input_dto.creator_roles),
                    requires_payment=input_dto.requires_payment,
                    mentor_exempt=input_dto.mentor_exempt,
                    plantilla_id=input_dto.plantilla_id,
                    activo=True,
                )
                for f in input_dto.fields:
                    FieldDefinition.objects.create(
                        tipo=tipo,
                        label=f.label,
                        field_type=f.field_type.value,
                        required=f.required,
                        order=f.order,
                        options=f.options,
                        accepted_extensions=f.accepted_extensions,
                        max_size_mb=f.max_size_mb,
                        max_chars=f.max_chars,
                        placeholder=f.placeholder,
                        help_text=f.help_text,
                    )
        except IntegrityError as exc:
            # Slug uniqueness is the only IntegrityError we expect on create —
            # `_build_unique_slug` makes this rare but a TOCTOU collision under
            # concurrent admin edits is still possible.
            if "slug" in str(exc).lower():
                raise TipoSlugConflict(f"slug={slug}") from exc
            raise
        return self.get_by_id(tipo.id)

    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO:
        try:
            with transaction.atomic():
                tipo = TipoSolicitud.objects.select_for_update().get(pk=input_dto.id)
                tipo.nombre = input_dto.nombre
                tipo.descripcion = input_dto.descripcion
                tipo.responsible_role = input_dto.responsible_role.value
                tipo.creator_roles = sorted(r.value for r in input_dto.creator_roles)
                tipo.requires_payment = input_dto.requires_payment
                tipo.mentor_exempt = input_dto.mentor_exempt
                tipo.plantilla_id = input_dto.plantilla_id
                tipo.save()
                self._replace_fields(tipo, input_dto)
        except TipoSolicitud.DoesNotExist as exc:
            raise TipoNotFound(f"id={input_dto.id}") from exc
        return self.get_by_id(tipo.id)

    def deactivate(self, tipo_id: UUID) -> None:
        updated = TipoSolicitud.objects.filter(pk=tipo_id).update(activo=False)
        if updated == 0:
            raise TipoNotFound(f"id={tipo_id}")

    def has_solicitudes(self, tipo_id: UUID) -> bool:
        # 004 will swap this for a real `Solicitud.objects.filter(...).exists()`.
        # Until then, the catalog cannot have downstream solicitudes, so
        # returning False keeps the gate honest.
        return False

    # ---- helpers ----

    def _replace_fields(
        self, tipo: TipoSolicitud, input_dto: UpdateTipoInput
    ) -> None:
        """Atomic upsert of the fieldset.

        Strategy: keep ids that were re-submitted (so historical FormSnapshots
        keep referring to the same field), update them in place, and create new
        rows for any input row without an id. Rows whose id is NOT in the
        input are deleted.
        """
        incoming_ids = {f.id for f in input_dto.fields if f.id is not None}
        FieldDefinition.objects.filter(tipo=tipo).exclude(pk__in=incoming_ids).delete()

        # Two-phase write to avoid colliding on the (tipo, order) unique
        # constraint when an admin reorders fields: park orders into a
        # disjoint range first, then write the real values. The offset must
        # exceed MAX_FIELDS_PER_TIPO so the parked range does not overlap any
        # legal new order; the assertion below pins that invariant in case
        # someone bumps the cap later.
        offset = 1000
        assert offset > MAX_FIELDS_PER_TIPO, "offset must exceed the per-tipo field cap"
        existing = {f.pk: f for f in FieldDefinition.objects.filter(tipo=tipo)}
        for f in existing.values():
            f.order += offset
        FieldDefinition.objects.bulk_update(existing.values(), ["order"])

        for inp in input_dto.fields:
            if inp.id is not None and inp.id in existing:
                row = existing[inp.id]
                row.label = inp.label
                row.field_type = inp.field_type.value
                row.required = inp.required
                row.order = inp.order
                row.options = inp.options
                row.accepted_extensions = inp.accepted_extensions
                row.max_size_mb = inp.max_size_mb
                row.max_chars = inp.max_chars
                row.placeholder = inp.placeholder
                row.help_text = inp.help_text
                row.save()
            else:
                FieldDefinition.objects.create(
                    tipo=tipo,
                    label=inp.label,
                    field_type=inp.field_type.value,
                    required=inp.required,
                    order=inp.order,
                    options=inp.options,
                    accepted_extensions=inp.accepted_extensions,
                    max_size_mb=inp.max_size_mb,
                    max_chars=inp.max_chars,
                    placeholder=inp.placeholder,
                    help_text=inp.help_text,
                )

    def _build_unique_slug(self, nombre: str) -> str:
        base = slugify(nombre)[:70] or "tipo"
        candidate = base
        n = 2
        while TipoSolicitud.objects.filter(slug=candidate).exists():
            suffix = f"-{n}"
            candidate = f"{base[: 80 - len(suffix)]}{suffix}"
            n += 1
        return candidate

    @staticmethod
    def _to_dto(tipo: TipoSolicitud) -> TipoSolicitudDTO:
        fields = [
            FieldDefinitionDTO(
                id=f.id,
                label=f.label,
                field_type=f.field_type,
                required=f.required,
                order=f.order,
                options=list(f.options or []),
                accepted_extensions=list(f.accepted_extensions or []),
                max_size_mb=f.max_size_mb,
                max_chars=f.max_chars,
                placeholder=f.placeholder,
                help_text=f.help_text,
            )
            for f in sorted(tipo.fields.all(), key=lambda r: r.order)
        ]
        return TipoSolicitudDTO(
            id=tipo.id,
            slug=tipo.slug,
            nombre=tipo.nombre,
            descripcion=tipo.descripcion,
            responsible_role=Role(tipo.responsible_role),
            creator_roles={Role(r) for r in tipo.creator_roles},
            requires_payment=tipo.requires_payment,
            mentor_exempt=tipo.mentor_exempt,
            plantilla_id=tipo.plantilla_id,
            activo=tipo.activo,
            fields=fields,
        )

    @staticmethod
    def _to_row(tipo: TipoSolicitud) -> TipoSolicitudRow:
        return TipoSolicitudRow(
            id=tipo.id,
            slug=tipo.slug,
            nombre=tipo.nombre,
            responsible_role=Role(tipo.responsible_role),
            creator_roles={Role(r) for r in tipo.creator_roles},
            requires_payment=tipo.requires_payment,
            activo=tipo.activo,
        )
