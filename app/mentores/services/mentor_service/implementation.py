"""Default :class:`MentorService` — orchestrates the repository + domain rules."""
from __future__ import annotations

import logging

from _shared.exceptions import DomainValidationError
from _shared.pagination import Page, PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorAlreadyActive
from mentores.repositories.mentor.interface import MentorRepository, UpsertOutcome
from mentores.schemas import MentorDTO, MentorUpsertInput
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

    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorDTO]:
        return self._repo.list(only_active=only_active, page=page)

    def add(
        self,
        *,
        matricula: str,
        fuente: MentorSource,
        nota: str,
        actor: UserDTO,
    ) -> MentorDTO:
        # ``AddMentorForm.clean_matricula`` already enforces the format on the
        # manual-add path. The check is repeated here because the CSV importer
        # bypasses Django forms entirely and goes straight to the service —
        # this is the authoritative gate for both paths.
        if not is_valid_matricula(matricula):
            raise DomainValidationError(
                matricula_format_message(),
                field_errors={"matricula": [matricula_format_message()]},
            )
        dto, outcome = self._repo.upsert(
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

    def deactivate(self, matricula: str, actor: UserDTO) -> MentorDTO:
        dto = self._repo.deactivate(matricula)
        self._logger.info(
            "mentor.deactivate matricula=%s actor=%s",
            matricula,
            actor.matricula,
        )
        return dto
