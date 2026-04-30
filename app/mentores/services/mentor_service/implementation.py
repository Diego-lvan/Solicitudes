"""Default :class:`MentorService` — orchestrates the repository + domain rules."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime

from _shared.exceptions import DomainValidationError
from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorAlreadyActive
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import (
    BulkDeactivateResult,
    MentorPeriodoDTO,
    MentorUpsertInput,
)
from mentores.services.mentor_service.interface import MentorService
from mentores.validators import is_valid_matricula, matricula_format_message
from usuarios.schemas import UserDTO


class DefaultMentorService(MentorService):
    """Coordinates catalog reads and writes around the domain invariants."""

    def __init__(
        self,
        *,
        mentor_repository: MentorRepository,
        logger: logging.Logger,
    ) -> None:
        self._repo = mentor_repository
        self._logger = logger

    def is_mentor(self, matricula: str) -> bool:
        return self._repo.exists_active(matricula)

    def list(
        self, *, only_active: bool, page: PageRequest
    ) -> Page[MentorPeriodoDTO]:
        return self._repo.list(only_active=only_active, page=page)

    def add(
        self,
        *,
        matricula: str,
        fuente: MentorSource,
        nota: str,
        actor: UserDTO,
    ) -> MentorPeriodoDTO:
        # ``AddMentorForm.clean_matricula`` already enforces the format on the
        # manual-add path. The check is repeated here because the CSV importer
        # bypasses Django forms entirely and goes straight to the service —
        # this is the authoritative gate for both paths.
        if not is_valid_matricula(matricula):
            raise DomainValidationError(
                matricula_format_message(),
                field_errors={"matricula": [matricula_format_message()]},
            )
        dto, outcome = self._repo.add_or_reactivate(
            MentorUpsertInput(
                matricula=matricula,
                fuente=fuente,
                nota=nota,
                creado_por_matricula=actor.matricula,
            )
        )
        if outcome is UpsertOutcome.ALREADY_ACTIVE:
            raise MentorAlreadyActive(f"matricula={matricula}")
        self._logger.info(
            "mentor.add matricula=%s actor=%s outcome=%s",
            matricula,
            actor.matricula,
            outcome.value,
        )
        return dto

    def deactivate(self, matricula: str, actor: UserDTO) -> MentorPeriodoDTO:
        dto = self._repo.deactivate(matricula, actor_matricula=actor.matricula)
        self._logger.info(
            "mentor.deactivate matricula=%s actor=%s",
            matricula,
            actor.matricula,
        )
        return dto

    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]:
        return self._repo.get_history(matricula)

    def was_mentor_at(self, matricula: str, when: datetime) -> bool:
        return self._repo.was_mentor_at(matricula, when)

    def bulk_deactivate(
        self, matriculas: Sequence[str], actor: UserDTO
    ) -> BulkDeactivateResult:
        # De-duplicate first: the underlying UPDATE collapses duplicate
        # matrículas in the IN clause, so a raw ``len(matriculas)`` would
        # over-count and surface false ``already_inactive`` numbers in the
        # admin flash message. After dedup, ``already_inactive`` cleanly
        # means "this matrícula has no currently-open period right now"
        # (closed or unknown) — the only honest interpretation we can give.
        unique_matriculas = list(set(matriculas))
        total = len(unique_matriculas)
        closed = self._repo.deactivate_many(
            unique_matriculas, actor_matricula=actor.matricula
        )
        result = BulkDeactivateResult(
            total_attempted=total,
            closed=closed,
            already_inactive=total - closed,
        )
        self._logger.info(
            "mentor.bulk_deactivate actor=%s attempted=%d closed=%d skipped=%d",
            actor.matricula,
            result.total_attempted,
            result.closed,
            result.already_inactive,
        )
        return result

    def deactivate_all_active(self, actor: UserDTO) -> BulkDeactivateResult:
        closed = self._repo.deactivate_all_active(actor_matricula=actor.matricula)
        result = BulkDeactivateResult(
            total_attempted=closed, closed=closed, already_inactive=0
        )
        self._logger.info(
            "mentor.deactivate_all_active actor=%s closed=%d",
            actor.matricula,
            closed,
        )
        return result
