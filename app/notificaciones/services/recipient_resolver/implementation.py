"""Default recipient resolver — delegates to :class:`UserService`."""
from __future__ import annotations

from notificaciones.services.recipient_resolver.interface import RecipientResolver
from usuarios.constants import Role
from usuarios.schemas import UserDTO
from usuarios.services.user_service.interface import UserService


class DefaultRecipientResolver(RecipientResolver):
    def __init__(self, *, user_service: UserService) -> None:
        self._users = user_service

    def resolve_by_role(self, role: Role) -> list[UserDTO]:
        return self._users.list_by_role(role)
