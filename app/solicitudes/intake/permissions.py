"""Permission mixins for intake views."""
from __future__ import annotations

from typing import ClassVar

from usuarios.constants import Role
from usuarios.permissions import RoleRequiredMixin


class CreatorRequiredMixin(RoleRequiredMixin):
    """Roles that can file solicitudes — alumnos and docentes."""

    required_roles: ClassVar[frozenset[Role]] = frozenset(
        {Role.ALUMNO, Role.DOCENTE}
    )
