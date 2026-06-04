"""Root pytest configuration.

Give every pytest *process* its own test database, regardless of which Django
settings module is active or how pytest was launched.

Background: the suite runs against the shared dev Postgres instance. By default
pytest-django only suffixes the test database name when running under xdist, so
ordinary runs all share one global ``test_solicitudes``. pytest-django drops and
recreates that database at session startup, so a second overlapping run — a
re-run before the last finished, a second terminal, or an IDE test runner that
uses the container's ``DJANGO_SETTINGS_MODULE=config.settings.dev`` — drops a
live run's database mid-session, surfacing as
``database "test_solicitudes" does not exist`` (with a matching "could not tear
down test databases" warning).

Overriding ``django_db_modify_db_settings`` here appends the OS process id to
the test database name for *any* settings module, so concurrent and repeated
runs stay independent. This mirrors pytest-django's own xdist-suffix logic.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def django_db_modify_db_settings() -> None:
    from django.conf import settings

    suffix = str(os.getpid())
    for db_settings in settings.DATABASES.values():
        if db_settings.get("ENGINE") == "django.db.backends.sqlite3":
            # In-memory/file SQLite is already per-process; nothing to isolate.
            continue
        test = db_settings.setdefault("TEST", {})
        base_name = test.get("NAME") or f"test_{db_settings['NAME']}"
        test["NAME"] = f"{base_name}_{suffix}"
