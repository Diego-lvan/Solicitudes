"""Tests for the {% lucide %} template tag."""
from __future__ import annotations

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
