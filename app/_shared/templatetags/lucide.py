"""Lucide icon template tag.

Renders a `<svg><use href=".../sprite.svg#name"></use></svg>` reference to the
vendored Lucide sprite at ``app/static/vendor/lucide/sprite.svg``.

The sprite is loaded once per page via ``components/lucide_sprite.html``; this
tag only renders the ``<use>`` reference, so per-icon HTML cost is ~80 bytes.

Usage::

    {% load lucide %}
    {% lucide "plus" %}
    {% lucide "trash-2" class="size-5 text-red-600" %}
    {% lucide "check" label="Listo" %}      {# accessible label, sets role=img #}

By default the icon is ``aria-hidden="true"`` (decorative). Pass ``label`` to
expose it to assistive tech.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import escape, format_html
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@lru_cache(maxsize=1)
def _sprite_markup() -> str:
    """Read the vendored sprite once per process, cache the bytes."""
    sprite_path = Path(settings.BASE_DIR) / "static" / "vendor" / "lucide" / "sprite.svg"
    try:
        return sprite_path.read_text()
    except FileNotFoundError:
        return ""


@register.simple_tag
def lucide_sprite() -> SafeString:
    """Inline the Lucide SVG sprite. Place once near the top of <body>.

    Inlining means the browser never makes a separate fetch for the sprite.
    Note: {% lucide %} still emits an absolute static URL ref
    (``/static/vendor/lucide/sprite.svg#name``); the inlined sprite is what
    those refs resolve against in modern browsers, and it also keeps the page
    working under strict CSP that forbids external SVG resources.
    """
    return mark_safe(_sprite_markup())


@register.simple_tag
def lucide(name: str, *, label: str = "", **kwargs: str) -> SafeString:
    css = kwargs.get("class", "size-4")
    href = f"{static('vendor/lucide/sprite.svg')}#{name}"
    if label:
        return format_html(
            '<svg class="{}" role="img" aria-label="{}"><use href="{}"></use></svg>',
            css,
            label,
            escape(href),
        )
    return format_html(
        '<svg class="{}" aria-hidden="true"><use href="{}"></use></svg>',
        css,
        escape(href),
    )
