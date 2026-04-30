"""Abstract user repository — boundary for ORM access from the service layer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from usuarios.constants import Role
from usuarios.schemas import CreateOrUpdateUserInput, UserDTO


class UserRepository(ABC):
    """Persistence boundary for usuarios.

    Implementations must translate Django ORM exceptions into feature-level
    exceptions (``UserNotFound``); ``Model.DoesNotExist`` must never escape.
    """

    @abstractmethod
    def get_by_matricula(self, matricula: str) -> UserDTO:
        """Return the user keyed by ``matricula`` or raise ``UserNotFound``."""

    @abstractmethod
    def upsert(self, input_dto: CreateOrUpdateUserInput) -> UserDTO:
        """Insert or update a user row and return the persisted DTO."""

    @abstractmethod
    def update_last_login(self, matricula: str, *, when: datetime) -> None:
        """Set ``last_login_at`` on an existing user; raise ``UserNotFound`` if missing."""

    @abstractmethod
    def list_by_role(self, role: Role) -> list[UserDTO]:
        """Return every user with ``role`` and a non-empty email, ordered by matricula.

        Used by ``notificaciones`` to fan out creation emails to every member
        of the responsible role. Recipients with empty emails are filtered
        here so service-layer callers don't re-implement the rule.
        """

    @abstractmethod
    def list_all(self, *, limit: int = 200) -> list[UserDTO]:
        """Return up to ``limit`` users, ordered by role then matricula.

        Used by the DEBUG-only dev-login picker; the cap is a defensive
        budget against rendering thousands of rows in a long-lived dev DB.
        Production code paths should not enumerate users — fetch by
        ``matricula`` instead.
        """
