"""Tier 2 E2E shared fixtures.

The browser tests under this folder run against `pytest-django`'s ``live_server``
(in-process Django on a random free port) and use ``pytest-playwright``'s
``page`` fixture. Per `.claude/skills/django-patterns/e2e.md`, this is the
default local-loop scenario — no Docker compose needed beyond the dev `web`
container that already runs everything.
"""
from __future__ import annotations

import os

# Playwright's sync API runs an asyncio event loop on the test thread. When
# pytest-django creates the test database, Django detects the running loop and
# refuses sync ORM calls unless this env var is set. Safe in tests because the
# DB calls run on the *test* thread, not inside an actual coroutine.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from collections.abc import Iterator
from importlib import reload

import pytest
from django.urls import clear_url_caches

import usuarios.urls


@pytest.fixture(autouse=True)
def _reload_urls_under_live_settings() -> Iterator[None]:
    """``usuarios.urls`` reads ``settings.DEBUG`` at import time. Earlier
    tests in this session may have reloaded it under DEBUG=False (see
    ``test_views_dev_login.py``), which would unmount ``/auth/dev-login``.
    Force a re-import here so the route is present for the browser test."""
    reload(usuarios.urls)
    clear_url_caches()
    yield
    reload(usuarios.urls)
    clear_url_caches()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, object]) -> dict[str, object]:
    """Default browser context for E2E: es-MX locale, América/Mexico_City
    timezone, fixed viewport so screenshots and ARIA snapshots are stable."""
    return {
        **browser_context_args,
        "locale": "es-MX",
        "timezone_id": "America/Mexico_City",
        "viewport": {"width": 1280, "height": 800},
    }
