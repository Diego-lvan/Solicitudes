"""Production settings — strict, env-driven, JSON logs."""
from __future__ import annotations

import os

from _shared.logging_config import build_logging_config

from .base import *  # noqa: F403

LOGGING = build_logging_config(json_format=True, level=os.environ.get("LOG_LEVEL", "INFO"))


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DEBUG = False
SECRET_KEY = _required("SECRET_KEY")
ALLOWED_HOSTS = [h.strip() for h in _required("ALLOWED_HOSTS").split(",") if h.strip()]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": _required("DB_HOST"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "NAME": _required("DB_NAME"),
        "USER": _required("DB_USER"),
        "PASSWORD": _required("DB_PASSWORD"),
        "CONN_MAX_AGE": 60,
    }
}

# Static files via WhiteNoise-friendly manifest storage.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = _required("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"

# Security hardening (TLS terminates at nginx; we only see X-Forwarded-Proto).
SECURE_SSL_REDIRECT = False  # nginx already redirects 80→443
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ("*",)
]
