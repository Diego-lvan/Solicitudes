"""Test settings — the default target for pytest (set in pyproject.toml).

The suite relies on Postgres-only ORM features (JSONField ``__contains``,
``DISTINCT ON``), so SQLite is not an option despite the historical "in-process,
SQLite" wording. Instead each pytest *process* gets its OWN test database name.

Why per-process: previously every run shared one global ``test_solicitudes`` on
the dev database. pytest-django drops and recreates the test database at session
startup, so a second overlapping run — a re-run before the last finished, a
second terminal, or an IDE test runner — would ``DROP DATABASE`` the live run's
database mid-session, surfacing as ``database "test_solicitudes" does not exist``
(with a matching "could not tear down" warning). A unique name per process makes
concurrent and repeated runs independent.

Inherits ``dev`` so application behaviour (auth URLs, CSRF origins, logging) is
identical to the dev runtime; only the test database name and email transport
differ. The dedicated postgres-test service (``config.settings.test_postgres``)
remains the opt-in path for `make e2e-postgres`.
"""
from __future__ import annotations

import os

from .dev import *  # noqa: F403

# Each pytest process targets its own test database so overlapping or repeated
# runs never drop one another's database out from under a live session.
DATABASES["default"].setdefault("TEST", {})  # noqa: F405
DATABASES["default"]["TEST"]["NAME"] = f"test_solicitudes_{os.getpid()}"  # noqa: F405

# Capture mail in-memory; tests must never reach the mailhog/SMTP transport.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
