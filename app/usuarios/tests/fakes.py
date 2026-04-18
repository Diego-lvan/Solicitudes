"""In-memory fakes used by service-layer tests.

Fakes implement the same interfaces as the real classes so they substitute
cleanly via constructor DI; no patching, no mocks across layer boundaries.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from _shared.auth import JwtClaims
from usuarios.constants import Role
from usuarios.exceptions import SigaUnavailable, UserNotFound
from usuarios.repositories.user.interface import UserRepository
from usuarios.schemas import CreateOrUpdateUserInput, SigaProfile, UserDTO
from usuarios.services.role_resolver.interface import RoleResolver
from usuarios.services.siga.interface import SigaService


class InMemoryUserRepository(UserRepository):
    """Dict-backed ``UserRepository`` for unit tests."""

    def __init__(self, seed: Iterable[UserDTO] | None = None) -> None:
        self._rows: dict[str, UserDTO] = {dto.matricula: dto for dto in (seed or [])}
        self._last_logins: dict[str, datetime] = {}

    def get_by_matricula(self, matricula: str) -> UserDTO:
        try:
            return self._rows[matricula]
        except KeyError as exc:
            raise UserNotFound(f"matricula={matricula}") from exc

    def upsert(self, input_dto: CreateOrUpdateUserInput) -> UserDTO:
        # Mirrors OrmUserRepository.upsert: empty strings / ``None`` are
        # interpreted as "no information" and never clobber the cached value.
        existing = self._rows.get(input_dto.matricula)
        merged = UserDTO(
            matricula=input_dto.matricula,
            email=input_dto.email,
            role=input_dto.role,
            full_name=input_dto.full_name or (existing.full_name if existing else ""),
            programa=input_dto.programa or (existing.programa if existing else ""),
            semestre=input_dto.semestre
            if input_dto.semestre is not None
            else (existing.semestre if existing else None),
        )
        self._rows[input_dto.matricula] = merged
        return merged

    def update_last_login(self, matricula: str, *, when: datetime) -> None:
        if matricula not in self._rows:
            raise UserNotFound(f"matricula={matricula}")
        self._last_logins[matricula] = when

    def list_all(self, *, limit: int = 200) -> list[UserDTO]:
        ordered = sorted(
            self._rows.values(),
            key=lambda dto: (dto.role.value, dto.matricula),
        )
        return ordered[:limit]

    # Test-only helpers
    def last_login_for(self, matricula: str) -> datetime | None:
        return self._last_logins.get(matricula)


class FakeRoleResolver(RoleResolver):
    """Returns a preset role; ignores the claims content."""

    def __init__(self, role: Role = Role.ALUMNO) -> None:
        self._role = role

    def resolve(self, claims: JwtClaims) -> Role:
        return self._role


class FakeSigaService(SigaService):
    """Returns a preset profile; can be configured to simulate failures."""

    def __init__(
        self,
        *,
        profile: SigaProfile | None = None,
        unavailable: bool = False,
        not_found: bool = False,
    ) -> None:
        self._profile = profile
        self._unavailable = unavailable
        self._not_found = not_found
        self.calls: list[str] = []

    def fetch_profile(self, matricula: str) -> SigaProfile:
        self.calls.append(matricula)
        if self._unavailable:
            raise SigaUnavailable("fake outage")
        if self._not_found or self._profile is None:
            raise UserNotFound(f"siga: matricula={matricula}")
        return self._profile
