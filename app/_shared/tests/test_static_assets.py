"""Sanity check: vendor static assets are real, not 0-byte placeholders.

Initiative 001 shipped placeholder files for the Bootstrap bundle with a
README telling future-us to replace them. The Playwright test exercises the
DOM but not CSS, so empty placeholders made the picker page look unstyled in
the browser without breaking any test. This guard prevents the regression.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings

VENDOR_FILES = (
    ("vendor/bootstrap/bootstrap.min.css", 50_000),
    ("vendor/bootstrap/bootstrap.bundle.min.js", 50_000),
    ("vendor/bootstrap-icons/bootstrap-icons.css", 20_000),
    ("vendor/bootstrap-icons/fonts/bootstrap-icons.woff2", 50_000),
)


@pytest.mark.parametrize(("relpath", "min_bytes"), VENDOR_FILES)
def test_vendor_file_is_not_a_placeholder(relpath: str, min_bytes: int) -> None:
    """Bootstrap bundle files exist with a plausibly-real size."""
    static_root = Path(settings.BASE_DIR) / "static"
    target = static_root / relpath
    assert target.is_file(), f"missing vendor file: {target}"
    size = target.stat().st_size
    assert size >= min_bytes, (
        f"{target} is {size} bytes; expected ≥ {min_bytes}. "
        "Did the placeholder files survive into the working tree? "
        "Re-fetch from https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/."
    )
