"""Re-exports for the permission mixin(s) used by ``reportes`` views."""
from __future__ import annotations

from usuarios.permissions import AdminRequiredMixin

__all__ = ["AdminRequiredMixin"]
