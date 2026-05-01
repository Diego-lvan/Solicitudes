"""Default implementation of :class:`UserDirectoryService`."""
from __future__ import annotations

import logging

from _shared.pagination import Page
from mentores.services.mentor_service.interface import MentorService
from usuarios.directory.repositories.user_directory.interface import (
    UserDirectoryRepository,
)
from usuarios.directory.schemas import UserDetail, UserListFilters, UserListItem
from usuarios.directory.services.user_directory.interface import (
    UserDirectoryService,
)


class DefaultUserDirectoryService(UserDirectoryService):
    def __init__(
        self,
        directory_repository: UserDirectoryRepository,
        mentor_service: MentorService,
        page_size: int,
        logger: logging.Logger,
    ) -> None:
        self._repo = directory_repository
        self._mentor = mentor_service
        self._page_size = page_size
        self._logger = logger

    def list(self, filters: UserListFilters) -> Page[UserListItem]:
        return self._repo.list(filters, self._page_size)

    def get_detail(self, matricula: str) -> UserDetail:
        detail = self._repo.get_detail(matricula)
        is_mentor: bool | None
        try:
            is_mentor = self._mentor.is_mentor(matricula)
        except Exception:
            # Best-effort overlay — surface "Desconocido" rather than 500 the page.
            self._logger.warning(
                "mentor_service.is_mentor failed for matricula=%s", matricula,
                exc_info=True,
            )
            is_mentor = None
        return detail.model_copy(update={"is_mentor": is_mentor})
