"""Constants for the plantilla_assets feature."""
from __future__ import annotations

MAX_ASSET_BYTES = 2 * 1024 * 1024  # 2 MB

ALLOWED_MIME = frozenset({"image/png", "image/jpeg", "image/webp"})

ALLOWED_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp"})
