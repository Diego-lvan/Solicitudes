"""Re-exports for the permission mixin(s) used by ``mentores`` views.

Centralizing the import here lets future migrations of the mixin module ripple
through one file rather than every view.
"""
from __future__ import annotations

from usuarios.permissions import AdminRequiredMixin

__all__ = ["AdminRequiredMixin"]
