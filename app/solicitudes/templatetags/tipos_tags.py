"""Template helpers for the tipos feature."""
from __future__ import annotations

from django import template

from solicitudes.tipos.constants import COMMON_FILE_EXTENSIONS

register = template.Library()


@register.simple_tag
def common_file_extensions() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Expose the predefined FILE-extension picker groups to templates.

    Returns the same tuple-of-tuples that ``COMMON_FILE_EXTENSIONS`` declares;
    templates iterate it to render a sectioned toggle group.
    """
    return COMMON_FILE_EXTENSIONS
