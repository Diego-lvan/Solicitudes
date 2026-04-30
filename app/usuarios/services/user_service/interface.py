"""Abstract user service — orchestrates repository + role + SIGA from the auth flow."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.auth import JwtClaims
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class UserService(ABC):
    """Application-facing operations on usuarios.

    Used by the auth middleware/views and by other features (via this interface,
    not the repository — see cross-feature dependency rule).
    """

    @abstractmethod
    def get_or_create_from_claims(self, claims: JwtClaims) -> UserDTO:
        """Upsert the user described by ``claims`` and stamp their last-login."""

    @abstractmethod
    def get_by_matricula(self, matricula: str) -> UserDTO:
        """Return the cached user; raise ``UserNotFound`` if absent."""

    @abstractmethod
    def hydrate_from_siga(self, matricula: str) -> UserDTO:
        """Best-effort enrichment from SIGA. Never raises ``SigaUnavailable``."""

    @abstractmethod
    def list_by_role(self, role: Role) -> list[UserDTO]:
        """Return every user with ``role`` and a deliverable email."""
