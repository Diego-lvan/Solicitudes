"""In-memory fakes for service-layer tests — no DB.

Mirrors :class:`OrmMentorRepository`'s contract against per-period storage.
The partial-uniqueness invariant is emulated via a Python check before
allocating a new period.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from itertools import count

from django.db import IntegrityError
from django.utils import timezone

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import MentorPeriodoDTO, MentorUpsertInput


class InMemoryMentorRepository(MentorRepository):
    """List-backed implementation. One entry per period, in insertion order."""

    def __init__(self) -> None:
        self._rows: list[MentorPeriodoDTO] = []
        self._ids = count(1)
        # Test hook: when truthy, the next ``add_or_reactivate`` raises
        # ``IntegrityError`` *after* the active-period check passes — used to
        # exercise the concurrent-reactivation recovery path.
        self._raise_integrity_error_once: MentorPeriodoDTO | None = None

    def exists_active(self, matricula: str) -> bool:
        return self._active_for(matricula) is not None

    def get_active_period(self, matricula: str) -> MentorPeriodoDTO:
        active = self._active_for(matricula)
        if active is None:
            raise MentorNotFound(f"matricula={matricula}")
        return active

    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorPeriodoDTO]:
        if only_active:
            rows = sorted(
                (r for r in self._rows if r.fecha_baja is None),
                key=lambda r: r.matricula,
            )
        else:
            # One row per matrícula: the most recent period (by fecha_alta).
            latest_by_matricula: dict[str, MentorPeriodoDTO] = {}
            for r in self._rows:
                cur = latest_by_matricula.get(r.matricula)
                if cur is None or r.fecha_alta > cur.fecha_alta:
                    latest_by_matricula[r.matricula] = r
            rows = sorted(latest_by_matricula.values(), key=lambda r: r.matricula)
        total = len(rows)
        start = page.offset
        end = start + page.page_size
        return Page[MentorPeriodoDTO](
            items=rows[start:end],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]:
        return sorted(
            (r for r in self._rows if r.matricula == matricula),
            key=lambda r: r.fecha_alta,
            reverse=True,
        )

    def was_mentor_at(self, matricula: str, when: datetime) -> bool:
        for r in self._rows:
            if r.matricula != matricula:
                continue
            if r.fecha_alta <= when and (r.fecha_baja is None or r.fecha_baja > when):
                return True
        return False

    def add_or_reactivate(
        self, input_dto: MentorUpsertInput
    ) -> tuple[MentorPeriodoDTO, UpsertOutcome]:
        active = self._active_for(input_dto.matricula)
        if active is not None:
            return active, UpsertOutcome.ALREADY_ACTIVE
        had_history = any(r.matricula == input_dto.matricula for r in self._rows)
        if self._raise_integrity_error_once is not None:
            # Simulate a concurrent reactivator winning the race: another
            # active period appears between our check and our insert.
            recovered = self._raise_integrity_error_once
            self._raise_integrity_error_once = None
            self._rows.append(recovered)
            try:
                raise IntegrityError("simulated partial unique index collision")
            except IntegrityError:
                # Recovery: re-read the active row and treat as no-op.
                return recovered, UpsertOutcome.ALREADY_ACTIVE
        new_row = MentorPeriodoDTO(
            id=next(self._ids),
            matricula=input_dto.matricula,
            fuente=input_dto.fuente,
            nota=input_dto.nota,
            fecha_alta=timezone.now(),
            fecha_baja=None,
            creado_por_matricula=input_dto.creado_por_matricula,
            desactivado_por_matricula=None,
        )
        self._rows.append(new_row)
        outcome = UpsertOutcome.REACTIVATED if had_history else UpsertOutcome.INSERTED
        return new_row, outcome

    def deactivate(
        self, matricula: str, *, actor_matricula: str
    ) -> MentorPeriodoDTO:
        active = self._active_for(matricula)
        if active is None:
            raise MentorNotFound(f"matricula={matricula}")
        closed = MentorPeriodoDTO(
            id=active.id,
            matricula=active.matricula,
            fuente=active.fuente,
            nota=active.nota,
            fecha_alta=active.fecha_alta,
            fecha_baja=timezone.now(),
            creado_por_matricula=active.creado_por_matricula,
            desactivado_por_matricula=actor_matricula,
        )
        idx = next(
            i
            for i, r in enumerate(self._rows)
            if r.matricula == matricula and r.fecha_baja is None
        )
        self._rows[idx] = closed
        return closed

    def deactivate_many(
        self, matriculas: Sequence[str], *, actor_matricula: str
    ) -> int:
        target = set(matriculas)
        if not target:
            return 0
        now = timezone.now()
        closed_count = 0
        for i, r in enumerate(self._rows):
            if r.matricula in target and r.fecha_baja is None:
                self._rows[i] = MentorPeriodoDTO(
                    id=r.id,
                    matricula=r.matricula,
                    fuente=r.fuente,
                    nota=r.nota,
                    fecha_alta=r.fecha_alta,
                    fecha_baja=now,
                    creado_por_matricula=r.creado_por_matricula,
                    desactivado_por_matricula=actor_matricula,
                )
                closed_count += 1
        return closed_count

    def deactivate_all_active(self, *, actor_matricula: str) -> int:
        now = timezone.now()
        closed_count = 0
        for i, r in enumerate(self._rows):
            if r.fecha_baja is None:
                self._rows[i] = MentorPeriodoDTO(
                    id=r.id,
                    matricula=r.matricula,
                    fuente=r.fuente,
                    nota=r.nota,
                    fecha_alta=r.fecha_alta,
                    fecha_baja=now,
                    creado_por_matricula=r.creado_por_matricula,
                    desactivado_por_matricula=actor_matricula,
                )
                closed_count += 1
        return closed_count

    # Test helpers ------------------------------------------------------
    def _active_for(self, matricula: str) -> MentorPeriodoDTO | None:
        for r in self._rows:
            if r.matricula == matricula and r.fecha_baja is None:
                return r
        return None

    def _seed(self, dto: MentorPeriodoDTO) -> None:
        self._rows.append(dto)
        # Keep the auto-id counter past the largest seeded id so new periods
        # don't collide with seeded ones.
        max_id = max(r.id for r in self._rows)
        self._ids = count(max_id + 1)

    def _seed_active(
        self, matricula: str, fuente: MentorSource = MentorSource.MANUAL
    ) -> MentorPeriodoDTO:
        dto = MentorPeriodoDTO(
            id=next(self._ids),
            matricula=matricula,
            fuente=fuente,
            nota="",
            fecha_alta=timezone.now(),
            fecha_baja=None,
            creado_por_matricula="ADM00000001",
            desactivado_por_matricula=None,
        )
        self._rows.append(dto)
        return dto

    def _arm_integrity_error(self, recovered: MentorPeriodoDTO) -> None:
        """Test hook: next ``add_or_reactivate`` raises and recovers to ``recovered``."""
        self._raise_integrity_error_once = recovered
