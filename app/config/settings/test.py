"""Test settings — the default target for pytest (set in pyproject.toml).

The suite relies on Postgres-only ORM features (JSONField ``__contains``,
``DISTINCT ON``), so SQLite is not an option despite the historical "in-process,
SQLite" wording. Tests therefore run against the dev Postgres instance.

Per-process test-database isolation (so concurrent or repeated runs never drop
one another's database) is handled in the root ``conftest.py`` rather than here,
because it must apply no matter which settings module pytest loads — the CLI
uses this module via ``--ds``, but IDE test runners often fall back to the
container's ``DJANGO_SETTINGS_MODULE=config.settings.dev``.

Inherits ``dev`` so application behaviour (auth URLs, CSRF origins, logging) is
identical to the dev runtime. The dedicated postgres-test service
(``config.settings.test_postgres``) remains the opt-in path for
`make e2e-postgres`.
"""
from __future__ import annotations

from .dev import *  # noqa: F403

# Capture mail in-memory; tests must never reach the mailhog/SMTP transport.
# (Django's test runner forces locmem too, but be explicit for non-pytest use.)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
