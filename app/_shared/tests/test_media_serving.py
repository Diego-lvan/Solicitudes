"""Media files must be served by the app itself.

On the full prod stack nginx serves ``/media/`` (see ``nginx/prod/nginx.conf``),
but the Railway demo runs only the ``web`` container — no nginx, and WhiteNoise
serves ``/static/`` only. Without an app-level media route every uploaded asset
(plantilla logos, sellos, firmas) returns 404 and the gallery thumbnails break,
which reads to users as "uploading images doesn't work".

This guards the app-served media path so the demo works without a fronting
proxy. In nginx-fronted deploys nginx short-circuits ``/media/`` before it ever
reaches Django, so this route is harmless there.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings


@pytest.fixture
def media_root(tmp_path: Path, settings) -> Path:  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def _read_body(response) -> bytes:  # type: ignore[no-untyped-def]
    if getattr(response, "streaming", False):
        return b"".join(response.streaming_content)
    return response.content


def test_uploaded_media_file_is_served(client, media_root: Path) -> None:
    """A file under MEDIA_ROOT is reachable at its MEDIA_URL with its bytes."""
    subdir = media_root / "plantilla_assets" / "2026" / "06"
    subdir.mkdir(parents=True)
    content = b"\x89PNG\r\n\x1a\nfake-png-bytes-for-serving-test"
    (subdir / "logo.png").write_bytes(content)

    url = f"{settings.MEDIA_URL}plantilla_assets/2026/06/logo.png"
    response = client.get(url)

    assert response.status_code == 200
    assert _read_body(response) == content


def test_missing_media_file_returns_404(client, media_root: Path) -> None:
    """A path with no file on disk still 404s (no path traversal / silent 200)."""
    response = client.get(f"{settings.MEDIA_URL}does/not/exist.png")
    assert response.status_code == 404
