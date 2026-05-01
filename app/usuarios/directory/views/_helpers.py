"""Shared helpers for directory views."""
from __future__ import annotations

from urllib.parse import urlencode, urlparse

from usuarios.directory.schemas import UserListFilters


_MAX_RETURN_LEN = 512


def safe_return_path(raw: str) -> str | None:
    """Return ``raw`` only if it is a safe same-origin relative path.

    A safe path:
      - is non-empty and at most ``_MAX_RETURN_LEN`` characters,
      - starts with a single ``/`` (not ``//`` — protocol-relative — and not a
        backslash variant),
      - has no scheme and no netloc (no ``http://`` etc.).

    Anything else (including absolute URLs to the same host) returns ``None`` so
    the caller can fall back to the canonical list URL.
    """
    if not raw or len(raw) > _MAX_RETURN_LEN:
        return None
    if not raw.startswith("/") or raw.startswith("//") or raw.startswith("/\\"):
        return None
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        return None
    return raw


def build_filter_querystring(filters: UserListFilters) -> str:
    """Build the ``role=…&q=…`` fragment used to preserve filters across links.

    Excludes ``page`` (callers add it themselves when building pagination links).
    Returns an empty string when no filter is active.
    """
    parts: dict[str, str] = {}
    if filters.role is not None:
        parts["role"] = filters.role.value
    if filters.q:
        parts["q"] = filters.q
    return urlencode(parts)
