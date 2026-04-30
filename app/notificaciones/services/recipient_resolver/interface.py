"""Resolves the audience for an outbound notification."""
from __future__ import annotations

from abc import ABC, abstractmethod

from usuarios.constants import Role
from usuarios.schemas import UserDTO


class RecipientResolver(ABC):
    """Look up the users who should receive a given notification."""

    @abstractmethod
    def resolve_by_role(self, role: Role) -> list[UserDTO]:
        """Return the active users with ``role`` whose email is deliverable."""
