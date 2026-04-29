"""Sanity check: vendor static assets are real, not 0-byte placeholders.

Initiative 001 shipped placeholder files for the (then-Bootstrap) bundle with
a README telling future-us to replace them. Initiative 015 swapped Bootstrap
for Tailwind v4 + Alpine.js + Lucide. The Playwright test exercises the DOM
but not CSS, so empty placeholders made the picker page look unstyled in the
browser without breaking any test. This guard prevents that regression on the
new vendor set.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings

VENDOR_FILES = (
    ("vendor/alpinejs/alpine.min.js", 30_000),
    ("vendor/alpinejs/alpine-collapse.min.js", 1_000),
    ("vendor/alpinejs/alpine-focus.min.js", 5_000),
    ("vendor/lucide/sprite.svg", 5_000),
    ("vendor/sortablejs/Sortable.min.js", 20_000),
    ("fonts/Inter/InterVariable.woff2", 200_000),
)


@pytest.mark.parametrize(("relpath", "min_bytes"), VENDOR_FILES)
def test_vendor_file_is_not_a_placeholder(relpath: str, min_bytes: int) -> None:
    """Vendor asset exists with a plausibly-real size."""
    static_root = Path(settings.BASE_DIR) / "static"
    target = static_root / relpath
    assert target.is_file(), f"missing vendor file: {target}"
    size = target.stat().st_size
    assert size >= min_bytes, (
        f"{target} is {size} bytes; expected ≥ {min_bytes}. "
        "If a vendor file went missing, re-fetch from the upstream release."
    )
