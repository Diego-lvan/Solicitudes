"""Template helpers for rendering role enums in human-readable Spanish.

Roles are stored as enum values like ``CONTROL_ESCOLAR`` (matches the auth
provider's vocabulary). For display the underscore must become a space and
the casing must be title-cased: ``CONTROL_ESCOLAR`` → ``Control Escolar``.
"""
from __future__ import annotations

from typing import Any

from django import template

register = template.Library()


@register.filter(name="role_label")
def role_label(value: Any) -> str:
    """Render an enum/string role as ``Title Cased`` with underscores → spaces."""
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw).replace("_", " ").title()
