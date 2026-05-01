"""ORM-backed implementation of :class:`UserDirectoryRepository`."""
from __future__ import annotations

from django.db.models import Q

from _shared.pagination import Page
from usuarios.constants import Role
from usuarios.directory.repositories.user_directory.interface import (
    UserDirectoryRepository,
)
from usuarios.directory.schemas import UserDetail, UserListFilters, UserListItem
from usuarios.exceptions import UserNotFound
from usuarios.models import User


class OrmUserDirectoryRepository(UserDirectoryRepository):
    def list(
        self, filters: UserListFilters, page_size: int
    ) -> Page[UserListItem]:
        qs = User.objects.all()
        if filters.role is not None:
            qs = qs.filter(role=filters.role.value)
        if filters.q:
            qs = qs.filter(
                Q(matricula__icontains=filters.q)
                | Q(full_name__icontains=filters.q)
                | Q(email__icontains=filters.q)
            )
        qs = qs.order_by("role", "matricula")
        total = qs.count()
        offset = (filters.page - 1) * page_size
        rows = list(qs[offset : offset + page_size])
        return Page[UserListItem](
            items=[self._to_list_item(row) for row in rows],
            total=total,
            page=filters.page,
            page_size=page_size,
        )

    def get_detail(self, matricula: str) -> UserDetail:
        try:
            user = User.objects.get(matricula=matricula)
        except User.DoesNotExist as exc:
            raise UserNotFound(f"matricula={matricula}") from exc
        return UserDetail(
            matricula=user.matricula,
            full_name=user.full_name,
            email=user.email,
            role=Role(user.role),
            programa=user.programa,
            semestre=user.semestre,
            gender=user.gender,
            is_mentor=None,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _to_list_item(user: User) -> UserListItem:
        return UserListItem(
            matricula=user.matricula,
            full_name=user.full_name,
            role=Role(user.role),
            programa=user.programa,
            email=user.email,
            last_login_at=user.last_login_at,
        )
