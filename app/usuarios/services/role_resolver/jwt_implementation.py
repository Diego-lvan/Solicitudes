"""JWT-claim-based role resolver."""
from __future__ import annotations

from _shared.auth import JwtClaims
from usuarios.constants import PROVIDER_ROLE_MAP, Role
from usuarios.exceptions import RoleNotRecognized
from usuarios.services.role_resolver.interface import RoleResolver


class JwtRoleResolver(RoleResolver):
    """Reads the ``rol`` claim and maps it to a :class:`Role` via ``PROVIDER_ROLE_MAP``."""

    def resolve(self, claims: JwtClaims) -> Role:
        try:
            return PROVIDER_ROLE_MAP[claims.rol.lower()]
        except KeyError as exc:
            raise RoleNotRecognized(f"unknown provider role: {claims.rol!r}") from exc
