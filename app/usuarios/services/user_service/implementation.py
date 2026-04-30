"""Default :class:`UserService` — wires repository + role resolver + SIGA."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from _shared.auth import JwtClaims
from usuarios.constants import Role
from usuarios.exceptions import SigaUnavailable
from usuarios.repositories.user.interface import UserRepository
from usuarios.schemas import CreateOrUpdateUserInput, UserDTO
from usuarios.services.role_resolver.interface import RoleResolver
from usuarios.services.siga.interface import SigaService
from usuarios.services.user_service.interface import UserService


class DefaultUserService(UserService):
    """Coordinates persistence, role mapping, and best-effort SIGA hydration."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        role_resolver: RoleResolver,
        siga_service: SigaService,
        logger: logging.Logger,
    ) -> None:
        self._repo = user_repository
        self._role_resolver = role_resolver
        self._siga = siga_service
        self._logger = logger

    def get_or_create_from_claims(self, claims: JwtClaims) -> UserDTO:
        role = self._role_resolver.resolve(claims)
        dto = self._repo.upsert(
            CreateOrUpdateUserInput(
                matricula=claims.sub,
                email=claims.email,
                role=role,
            )
        )
        self._repo.update_last_login(claims.sub, when=datetime.now(tz=UTC))
        return dto

    def get_by_matricula(self, matricula: str) -> UserDTO:
        return self._repo.get_by_matricula(matricula)

    def list_by_role(self, role: Role) -> list[UserDTO]:
        return self._repo.list_by_role(role)

    def hydrate_from_siga(self, matricula: str) -> UserDTO:
        existing = self._repo.get_by_matricula(matricula)
        try:
            profile = self._siga.fetch_profile(matricula)
        except SigaUnavailable as exc:
            self._logger.warning("siga.skip matricula=%s reason=%s", matricula, exc)
            return existing
        # Email is owned by the auth provider (security-of-record); SIGA only
        # enriches academic profile fields. Never let SIGA rewrite the email
        # used for identity lookups.
        return self._repo.upsert(
            CreateOrUpdateUserInput(
                matricula=matricula,
                email=existing.email,
                role=existing.role,
                full_name=profile.full_name,
                programa=profile.programa,
                semestre=profile.semestre,
            )
        )
