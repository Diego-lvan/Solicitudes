"""Abstract :class:`UserDirectoryRepository` — read-only access to ``usuarios.User``."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.pagination import Page
from usuarios.directory.schemas import UserDetail, UserListFilters, UserListItem


class UserDirectoryRepository(ABC):
    @abstractmethod
    def list(
        self, filters: UserListFilters, page_size: int
    ) -> Page[UserListItem]:
        """Filtered, ordered, paginated list of users."""

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail:
        """Return the full detail (with ``is_mentor=None`` — service overlays it).

        Raises:
            usuarios.exceptions.UserNotFound: when ``matricula`` does not exist.
        """
