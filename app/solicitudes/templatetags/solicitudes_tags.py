"""Template helpers for solicitudes intake/revision rendering."""
from __future__ import annotations

from typing import Any

from django import template

register = template.Library()


@register.filter(name="get_valor")
def get_valor(valores: dict[str, Any] | None, field_id: Any) -> Any:
    """Look up a snapshot field value by id (UUID or str). Returns ``""`` if absent."""
    if not valores:
        return ""
    key = str(field_id)
    return valores.get(key, "")
