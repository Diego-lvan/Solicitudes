"""Abstract :class:`UserDirectoryService` — application-facing read operations."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.pagination import Page
from usuarios.directory.schemas import UserDetail, UserListFilters, UserListItem


class UserDirectoryService(ABC):
    @abstractmethod
    def list(self, filters: UserListFilters) -> Page[UserListItem]:
        """Filtered, ordered, paginated list."""

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail:
        """Full detail with mentor status overlaid.

        ``is_mentor`` is ``True`` / ``False`` when the mentor service responds,
        and ``None`` when it raises (the failure is logged at WARNING).

        Raises:
            usuarios.exceptions.UserNotFound: when ``matricula`` does not exist.
        """
