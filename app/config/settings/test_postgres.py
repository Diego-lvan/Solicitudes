"""Opt-in test settings that target the postgres-test compose service.

Use with: pytest --ds=config.settings.test_postgres
"""
from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret"
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "postgres-test",
        "PORT": "5432",
        "NAME": "solicitudes_test",
        "USER": "test",
        "PASSWORD": "test",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
