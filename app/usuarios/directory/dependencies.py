"""DI factory functions for the user directory feature."""
from __future__ import annotations

import logging

from mentores.dependencies import get_mentor_service
from usuarios.directory.constants import PAGE_SIZE
from usuarios.directory.repositories.user_directory import (
    OrmUserDirectoryRepository,
    UserDirectoryRepository,
)
from usuarios.directory.services.user_directory import (
    DefaultUserDirectoryService,
    UserDirectoryService,
)


def get_user_directory_repository() -> UserDirectoryRepository:
    return OrmUserDirectoryRepository()


def get_user_directory_service() -> UserDirectoryService:
    return DefaultUserDirectoryService(
        directory_repository=get_user_directory_repository(),
        mentor_service=get_mentor_service(),
        page_size=PAGE_SIZE,
        logger=logging.getLogger("usuarios.directory.service"),
    )
