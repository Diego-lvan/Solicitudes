"""ORM-backed implementation of :class:`MentorRepository`."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.models import Mentor
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import MentorDTO, MentorUpsertInput


class OrmMentorRepository(MentorRepository):
    """Django ORM implementation. Owns all access to the ``Mentor`` model."""

    def get_by_matricula(self, matricula: str) -> MentorDTO:
        try:
            mentor = Mentor.objects.get(pk=matricula)
        except Mentor.DoesNotExist as exc:
            raise MentorNotFound(f"matricula={matricula}") from exc
        return self._to_dto(mentor)

    def exists_active(self, matricula: str) -> bool:
        return Mentor.objects.filter(pk=matricula, activo=True).exists()

    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorDTO]:
        qs = Mentor.objects.all()
        if only_active:
            qs = qs.filter(activo=True)
        qs = qs.order_by("matricula")
        total = qs.count()
        rows = qs[page.offset : page.offset + page.page_size]
        return Page[MentorDTO](
            items=[self._to_dto(m) for m in rows],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    def upsert(self, input_dto: MentorUpsertInput) -> tuple[MentorDTO, UpsertOutcome]:
        # Reactivation must rewrite ``fecha_alta``; ``auto_now_add`` only fires
        # on insert, so we update it explicitly when flipping ``activo`` back on.
        with transaction.atomic():
            existing = (
                Mentor.objects.select_for_update().filter(pk=input_dto.matricula).first()
            )
            if existing is None:
                mentor = Mentor.objects.create(
                    matricula=input_dto.matricula,
                    activo=True,
                    fuente=input_dto.fuente.value,
                    nota=input_dto.nota,
                    creado_por_id=input_dto.creado_por_matricula,
                )
                return self._to_dto(mentor), UpsertOutcome.INSERTED
            if existing.activo:
                return self._to_dto(existing), UpsertOutcome.ALREADY_ACTIVE
            existing.activo = True
            existing.fecha_alta = timezone.now()
            existing.fecha_baja = None
            existing.fuente = input_dto.fuente.value
            if input_dto.nota:
                existing.nota = input_dto.nota
            existing.creado_por_id = input_dto.creado_por_matricula
            existing.save(
                update_fields=[
                    "activo",
                    "fecha_alta",
                    "fecha_baja",
                    "fuente",
                    "nota",
                    "creado_por",
                ]
            )
            return self._to_dto(existing), UpsertOutcome.REACTIVATED

    def deactivate(self, matricula: str) -> MentorDTO:
        with transaction.atomic():
            try:
                mentor = Mentor.objects.select_for_update().get(pk=matricula)
            except Mentor.DoesNotExist as exc:
                raise MentorNotFound(f"matricula={matricula}") from exc
            if not mentor.activo:
                return self._to_dto(mentor)
            mentor.activo = False
            mentor.fecha_baja = timezone.now()
            mentor.save(update_fields=["activo", "fecha_baja"])
            return self._to_dto(mentor)

    @staticmethod
    def _to_dto(mentor: Mentor) -> MentorDTO:
        return MentorDTO(
            matricula=mentor.matricula,
            activo=mentor.activo,
            fuente=MentorSource(mentor.fuente),
            nota=mentor.nota,
            fecha_alta=mentor.fecha_alta,
            fecha_baja=mentor.fecha_baja,
        )
