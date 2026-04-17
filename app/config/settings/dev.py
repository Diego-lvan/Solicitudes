"""Development settings — DEBUG=True, SQLite, console-friendly logging."""
from __future__ import annotations

import os

from _shared.logging_config import build_logging_config

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-not-for-prod")

LOGGING = build_logging_config(json_format=False, level=os.environ.get("LOG_LEVEL", "DEBUG"))

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "mailhog")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_USE_TLS = False

# CSRF: dev goes through nginx on https://localhost
CSRF_TRUSTED_ORIGINS = ["https://localhost", "http://localhost"]

# Postgres in dev container, SQLite fallback when running outside Docker.
if os.environ.get("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["DB_HOST"],
            "PORT": os.environ.get("DB_PORT", "5432"),
            "NAME": os.environ.get("DB_NAME", "solicitudes"),
            "USER": os.environ.get("DB_USER", "solicitudes"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "solicitudes"),
        }
    }
