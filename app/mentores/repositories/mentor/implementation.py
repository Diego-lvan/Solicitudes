"""ORM-backed implementation of :class:`MentorRepository` against ``MentorPeriodo``."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.models import MentorPeriodo
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import MentorPeriodoDTO, MentorUpsertInput


class OrmMentorRepository(MentorRepository):
    """Django ORM implementation. Owns all access to ``MentorPeriodo``."""

    def exists_active(self, matricula: str) -> bool:
        return MentorPeriodo.objects.filter(
            matricula=matricula, fecha_baja__isnull=True
        ).exists()

    def get_active_period(self, matricula: str) -> MentorPeriodoDTO:
        try:
            periodo = MentorPeriodo.objects.get(
                matricula=matricula, fecha_baja__isnull=True
            )
        except MentorPeriodo.DoesNotExist as exc:
            raise MentorNotFound(f"matricula={matricula}") from exc
        return self._to_dto(periodo)

    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorPeriodoDTO]:
        if only_active:
            qs = MentorPeriodo.objects.filter(fecha_baja__isnull=True).order_by(
                "matricula"
            )
            total = qs.count()
            rows = list(qs[page.offset : page.offset + page.page_size])
        else:
            # One row per matrícula: the most recent period via Postgres
            # DISTINCT ON. Admins see a single summary entry per person; the
            # row's ``fecha_baja`` says whether they're currently active.
            base = MentorPeriodo.objects.order_by(
                "matricula", "-fecha_alta"
            ).distinct("matricula")
            total = base.count()
            rows = list(base[page.offset : page.offset + page.page_size])
        return Page[MentorPeriodoDTO](
            items=[self._to_dto(p) for p in rows],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]:
        rows = MentorPeriodo.objects.filter(matricula=matricula).order_by(
            "-fecha_alta"
        )
        return [self._to_dto(p) for p in rows]

    def was_mentor_at(self, matricula: str, when: datetime) -> bool:
        # Half-open ``[fecha_alta, fecha_baja)``: alta inclusive, baja exclusive.
        return (
            MentorPeriodo.objects.filter(matricula=matricula, fecha_alta__lte=when)
            .filter(Q(fecha_baja__isnull=True) | Q(fecha_baja__gt=when))
            .exists()
        )

    def add_or_reactivate(
        self, input_dto: MentorUpsertInput
    ) -> tuple[MentorPeriodoDTO, UpsertOutcome]:
        # Two reads + one write. The "exists active?" check covers the common
        # case; the partial unique index is the safety net under concurrent
        # admin actions. Without IntegrityError recovery, a TOCTOU race between
        # two reactivation requests would surface as a 500.
        with transaction.atomic():
            active = MentorPeriodo.objects.filter(
                matricula=input_dto.matricula, fecha_baja__isnull=True
            ).first()
            if active is not None:
                return self._to_dto(active), UpsertOutcome.ALREADY_ACTIVE
            had_history = MentorPeriodo.objects.filter(
                matricula=input_dto.matricula
            ).exists()
            try:
                new_period = MentorPeriodo.objects.create(
                    matricula=input_dto.matricula,
                    fuente=input_dto.fuente.value,
                    nota=input_dto.nota,
                    fecha_alta=timezone.now(),
                    creado_por_id=input_dto.creado_por_matricula,
                )
            except IntegrityError:
                # Concurrent reactivator won the race against the partial
                # unique index. Re-read the active row and treat as no-op.
                active = MentorPeriodo.objects.get(
                    matricula=input_dto.matricula, fecha_baja__isnull=True
                )
                return self._to_dto(active), UpsertOutcome.ALREADY_ACTIVE
        outcome = UpsertOutcome.REACTIVATED if had_history else UpsertOutcome.INSERTED
        return self._to_dto(new_period), outcome

    def deactivate(
        self, matricula: str, *, actor_matricula: str
    ) -> MentorPeriodoDTO:
        with transaction.atomic():
            try:
                periodo = MentorPeriodo.objects.select_for_update().get(
                    matricula=matricula, fecha_baja__isnull=True
                )
            except MentorPeriodo.DoesNotExist as exc:
                raise MentorNotFound(f"matricula={matricula}") from exc
            periodo.fecha_baja = timezone.now()
            periodo.desactivado_por_id = actor_matricula
            periodo.save(update_fields=["fecha_baja", "desactivado_por"])
            return self._to_dto(periodo)

    def deactivate_many(
        self, matriculas: Sequence[str], *, actor_matricula: str
    ) -> int:
        # Empty input shortcuts so we don't issue a no-op UPDATE round trip.
        if not matriculas:
            return 0
        return MentorPeriodo.objects.filter(
            matricula__in=matriculas, fecha_baja__isnull=True
        ).update(
            fecha_baja=timezone.now(),
            desactivado_por_id=actor_matricula,
        )

    def deactivate_all_active(self, *, actor_matricula: str) -> int:
        return MentorPeriodo.objects.filter(fecha_baja__isnull=True).update(
            fecha_baja=timezone.now(),
            desactivado_por_id=actor_matricula,
        )

    @staticmethod
    def _to_dto(periodo: MentorPeriodo) -> MentorPeriodoDTO:
        return MentorPeriodoDTO(
            id=periodo.pk,
            matricula=periodo.matricula,
            fuente=MentorSource(periodo.fuente),
            nota=periodo.nota,
            fecha_alta=periodo.fecha_alta,
            fecha_baja=periodo.fecha_baja,
            creado_por_matricula=periodo.creado_por_id,
            desactivado_por_matricula=periodo.desactivado_por_id,
        )
