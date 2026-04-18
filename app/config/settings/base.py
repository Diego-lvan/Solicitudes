"""Shared Django settings for all environments."""
from __future__ import annotations

import os
from pathlib import Path

# /app/ inside container; the host's ./app/ on the developer machine.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    # No django.contrib.admin: RNF-01 mandates external auth provider; the admin
    # would have no valid login flow and no users with `is_staff`.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "_shared",
    "usuarios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "_shared.middleware.request_id.RequestIDMiddleware",
    "_shared.middleware.logging.StructuredLoggingMiddleware",
    "usuarios.middleware.JwtAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "_shared.middleware.error_handler.AppErrorMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "usuarios.User"

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@uaz.edu.mx")

LOGIN_URL = os.environ.get("AUTH_PROVIDER_LOGIN_URL", "/auth/login/")
LOGIN_REDIRECT_URL = LOGIN_URL

# Auth provider integration (initiative 002).
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
AUTH_PROVIDER_LOGIN_URL = LOGIN_URL
AUTH_PROVIDER_LOGOUT_URL = os.environ.get("AUTH_PROVIDER_LOGOUT_URL", "")

# SIGA (academic information system) integration.
SIGA_BASE_URL = os.environ.get("SIGA_BASE_URL", "")
SIGA_TIMEOUT_SECONDS = float(os.environ.get("SIGA_TIMEOUT_SECONDS", "5"))

SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://localhost")

# Behind nginx, trust the X-Forwarded-Proto header for request.is_secure().
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Logging — built by _shared.logging_config
from _shared.logging_config import build_logging_config  # noqa: E402

LOGGING = build_logging_config(json_format=False, level="INFO")
