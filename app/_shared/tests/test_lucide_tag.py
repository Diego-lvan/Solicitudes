"""Tests for the {% lucide %} template tag."""
from __future__ import annotations

import pytest
from django.template import Context, Template


def _render(template_src: str, **ctx: object) -> str:
    return Template("{% load lucide %}" + template_src).render(Context(ctx))


def test_default_renders_decorative_svg_with_size_4_class() -> None:
    out = _render('{% lucide "plus" %}')
    assert '<svg class="size-4" aria-hidden="true">' in out
    assert "/static/vendor/lucide/sprite.svg#plus" in out
    assert "</use></svg>" in out
    assert "role=" not in out  # decorative icons must not advertise role=img


def test_class_kwarg_overrides_default_classes() -> None:
    out = _render('{% lucide "trash-2" class="size-5 text-red-600" %}')
    assert 'class="size-5 text-red-600"' in out
    assert "sprite.svg#trash-2" in out


def test_label_kwarg_promotes_to_role_img_with_aria_label() -> None:
    out = _render('{% lucide "check" label="Listo" %}')
    assert 'role="img"' in out
    assert 'aria-label="Listo"' in out
    assert "aria-hidden" not in out


def test_label_is_html_escaped() -> None:
    out = _render('{% lucide "check" label=evil %}', evil='<script>x</script>')
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_sprite_markup_returns_empty_when_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the vendored sprite is absent, ``_sprite_markup`` degrades to an
    empty string instead of raising."""
    from pathlib import Path

    import _shared.templatetags.lucide as lucide_mod

    def _raise(self: Path, *args: object, **kwargs: object) -> str:
        raise FileNotFoundError

    # The result is lru_cached; clear it so the patched read is observed.
    lucide_mod._sprite_markup.cache_clear()
    monkeypatch.setattr(Path, "read_text", _raise)  # type: ignore[arg-type]
    try:
        assert lucide_mod._sprite_markup() == ""
    finally:
        lucide_mod._sprite_markup.cache_clear()
