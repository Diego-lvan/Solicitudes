"""Abstract role resolver — turns provider claims into our internal :class:`Role`."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.auth import JwtClaims
from usuarios.constants import Role


class RoleResolver(ABC):
    """Strategy for deriving a :class:`Role` from the JWT.

    A second implementation backed by an internal directory table is anticipated
    if the provider's JWT does not carry personal roles (OQ-002-2); the ABC
    insulates the rest of the codebase from that change.
    """

    @abstractmethod
    def resolve(self, claims: JwtClaims) -> Role:
        """Return the user's :class:`Role` or raise ``RoleNotRecognized``."""
