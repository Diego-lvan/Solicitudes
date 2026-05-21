"""Re-export the admin mixin to keep cross-app coupling explicit."""
from __future__ import annotations

from usuarios.permissions import AdminRequiredMixin

__all__ = ["AdminRequiredMixin"]
