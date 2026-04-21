"""Permission mixins for revision views."""
from __future__ import annotations

from typing import ClassVar

from usuarios.constants import Role
from usuarios.permissions import RoleRequiredMixin


class ReviewerRequiredMixin(RoleRequiredMixin):
    """Roles that can review/take/finalize/cancel solicitudes (everyone but creators)."""

    required_roles: ClassVar[frozenset[Role]] = frozenset(
        {Role.CONTROL_ESCOLAR, Role.RESPONSABLE_PROGRAMA, Role.DOCENTE, Role.ADMIN}
    )
