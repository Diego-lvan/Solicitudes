"""ORM-backed implementation of :class:`UserRepository`."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction

from usuarios.constants import Role
from usuarios.exceptions import UserNotFound
from usuarios.models import User
from usuarios.repositories.user.interface import UserRepository
from usuarios.schemas import CreateOrUpdateUserInput, UserDTO


class OrmUserRepository(UserRepository):
    """Django ORM implementation. Owns all access to the ``User`` model."""

    def get_by_matricula(self, matricula: str) -> UserDTO:
        try:
            user = User.objects.get(pk=matricula)
        except User.DoesNotExist as exc:
            raise UserNotFound(f"matricula={matricula}") from exc
        return self._to_dto(user)

    def upsert(self, input_dto: CreateOrUpdateUserInput) -> UserDTO:
        # Only fields the caller actually populated overwrite the row. Empty
        # strings / ``None`` mean "no information", not "clear it" — a JWT-only
        # login (no SIGA data) must not clobber the cached `full_name`,
        # `programa`, or `semestre` from a previous SIGA hydration.
        defaults: dict[str, object] = {
            "email": input_dto.email,
            "role": input_dto.role.value,
        }
        if input_dto.full_name:
            defaults["full_name"] = input_dto.full_name
        if input_dto.programa:
            defaults["programa"] = input_dto.programa
        if input_dto.semestre is not None:
            defaults["semestre"] = input_dto.semestre
        if input_dto.gender:
            defaults["gender"] = input_dto.gender
        with transaction.atomic():
            user, _ = User.objects.update_or_create(
                matricula=input_dto.matricula,
                defaults=defaults,
            )
        return self._to_dto(user)

    def update_last_login(self, matricula: str, *, when: datetime) -> None:
        updated = User.objects.filter(pk=matricula).update(last_login_at=when)
        if updated == 0:
            raise UserNotFound(f"matricula={matricula}")

    def list_by_role(self, role: Role) -> list[UserDTO]:
        return [
            self._to_dto(u)
            for u in User.objects.filter(role=role.value)
            .exclude(email="")
            .order_by("matricula")
        ]

    def list_all(self, *, limit: int = 200) -> list[UserDTO]:
        return [
            self._to_dto(u)
            for u in User.objects.order_by("role", "matricula")[:limit]
        ]

    @staticmethod
    def _to_dto(user: User) -> UserDTO:
        return UserDTO(
            matricula=user.matricula,
            email=user.email,
            role=Role(user.role),
            full_name=user.full_name,
            programa=user.programa,
            semestre=user.semestre,
            gender=user.gender,
        )
