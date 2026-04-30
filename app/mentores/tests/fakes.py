"""In-memory fakes for service-layer tests — no DB."""
from __future__ import annotations

from django.utils import timezone

from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import MentorDTO, MentorUpsertInput


class InMemoryMentorRepository(MentorRepository):
    """Dict-backed implementation. Mirrors :class:`OrmMentorRepository`'s contract."""

    def __init__(self) -> None:
        self._rows: dict[str, MentorDTO] = {}

    def get_by_matricula(self, matricula: str) -> MentorDTO:
        try:
            return self._rows[matricula]
        except KeyError as exc:
            raise MentorNotFound(f"matricula={matricula}") from exc

    def exists_active(self, matricula: str) -> bool:
        row = self._rows.get(matricula)
        return bool(row and row.activo)

    def list(
        self,
        *,
        only_active: bool,
        page: PageRequest,
    ) -> Page[MentorDTO]:
        rows = sorted(self._rows.values(), key=lambda m: m.matricula)
        if only_active:
            rows = [r for r in rows if r.activo]
        total = len(rows)
        start = page.offset
        end = start + page.page_size
        return Page[MentorDTO](
            items=rows[start:end],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    def upsert(self, input_dto: MentorUpsertInput) -> tuple[MentorDTO, UpsertOutcome]:
        existing = self._rows.get(input_dto.matricula)
        now = timezone.now()
        if existing is None:
            dto = MentorDTO(
                matricula=input_dto.matricula,
                activo=True,
                fuente=input_dto.fuente,
                nota=input_dto.nota,
                fecha_alta=now,
                fecha_baja=None,
            )
            self._rows[input_dto.matricula] = dto
            return dto, UpsertOutcome.INSERTED
        if existing.activo:
            return existing, UpsertOutcome.ALREADY_ACTIVE
        dto = MentorDTO(
            matricula=existing.matricula,
            activo=True,
            fuente=input_dto.fuente,
            nota=input_dto.nota or existing.nota,
            fecha_alta=now,
            fecha_baja=None,
        )
        self._rows[existing.matricula] = dto
        return dto, UpsertOutcome.REACTIVATED

    def deactivate(self, matricula: str) -> MentorDTO:
        existing = self._rows.get(matricula)
        if existing is None:
            raise MentorNotFound(f"matricula={matricula}")
        if not existing.activo:
            return existing
        dto = MentorDTO(
            matricula=existing.matricula,
            activo=False,
            fuente=existing.fuente,
            nota=existing.nota,
            fecha_alta=existing.fecha_alta,
            fecha_baja=timezone.now(),
        )
        self._rows[matricula] = dto
        return dto

    # Test helpers ------------------------------------------------------
    def _seed(self, dto: MentorDTO) -> None:
        self._rows[dto.matricula] = dto

    def _seed_active(self, matricula: str, fuente: MentorSource = MentorSource.MANUAL) -> None:
        self._seed(
            MentorDTO(
                matricula=matricula,
                activo=True,
                fuente=fuente,
                nota="",
                fecha_alta=timezone.now(),
                fecha_baja=None,
            )
        )
