# Platform — Shared Infrastructure

Cross-cutting modules under `_shared/`, plus base templates, settings layout, and URL roots. None of this is domain logic; it's the glue every feature depends on.

---

## `_shared/` layout

```
_shared/
├── __init__.py
├── exceptions.py              # AppError + sentinel exceptions
├── middleware.py              # Cross-cutting middleware
├── auth.py                    # JWT validation helpers
├── pagination.py              # Page request/response DTOs
├── pdf.py                     # WeasyPrint wrapper
└── tests/
    ├── test_exceptions.py
    └── test_middleware.py
```

`_shared/` contains exactly modules that **every feature depends on**. If only one feature uses something, it belongs in that feature, not here.

---

## `_shared/middleware.py`

```python
"""Cross-cutting middleware: request ID, error handler, structured logging."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from _shared.exceptions import AppError

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """Attach a request ID to every request and propagate it to the response.

    Uses an inbound X-Request-ID header if present, otherwise generates one.
    """
    HEADER = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        rid = request.headers.get(self.HEADER) or uuid.uuid4().hex
        request.request_id = rid  # type: ignore[attr-defined]
        response = self.get_response(request)
        response[self.HEADER] = rid
        return response


class StructuredLoggingMiddleware:
    """Log one structured line per request with timing and outcome."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request",
            extra={
                "request_id": getattr(request, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms,
                "user_id": getattr(request.user, "id", None) if hasattr(request, "user") else None,
            },
        )
        return response


class AppErrorMiddleware:
    """Catch uncaught AppError and render a uniform response (HTML or JSON)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        if not isinstance(exception, AppError):
            return None

        logger.warning(
            "AppError",
            extra={
                "request_id": getattr(request, "request_id", None),
                "code": exception.code,
                "detail": exception.detail,
                "path": request.path,
            },
        )

        if self._wants_json(request):
            return JsonResponse(
                {"error": {"code": exception.code, "message": exception.user_message}},
                status=exception.http_status,
            )
        return render(
            request,
            "_shared/error.html",
            {"code": exception.code, "message": exception.user_message},
            status=exception.http_status,
        )

    @staticmethod
    def _wants_json(request: HttpRequest) -> bool:
        return (
            "application/json" in request.headers.get("Accept", "")
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )
```

Order in `MIDDLEWARE` matters:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "_shared.middleware.RequestIDMiddleware",          # first — assigns request_id
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "_shared.middleware.StructuredLoggingMiddleware",  # logs each request
    "_shared.middleware.AppErrorMiddleware",           # catches uncaught AppError
]
```

---

## `_shared/auth.py` — JWT validation helpers

```python
"""JWT validation helpers used by the auth middleware (or DRF-style auth class).

This module is pure Python — it does not import HttpRequest. The middleware that
calls it is the boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import jwt

from _shared.exceptions import Unauthorized


@dataclass(frozen=True)
class JWTClaims:
    user_id: UUID
    email: str
    role: str
    issued_at: datetime
    expires_at: datetime


def decode_jwt(token: str, *, secret: str, algorithms: list[str]) -> JWTClaims:
    """Decode and validate a JWT. Raises Unauthorized on any failure."""
    try:
        payload = jwt.decode(token, secret, algorithms=algorithms)
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token expirado")
    except jwt.InvalidTokenError as e:
        raise Unauthorized(f"Token inválido: {e}")

    return JWTClaims(
        user_id=UUID(payload["sub"]),
        email=payload["email"],
        role=payload.get("role", "alumno"),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )
```

The auth middleware (in the `usuarios` app, not `_shared`) calls `decode_jwt`, sets `request.user`, and rejects unauthenticated requests for protected URLs.

---

## `_shared/pagination.py`

```python
"""Pagination DTOs."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


class PageRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        return self.page > 1
```

Repository methods that paginate accept `PageRequest` and return `Page[SolicitudRow]`.

---

## `_shared/pdf.py`

```python
"""WeasyPrint wrapper. Pure function; no Django dependencies beyond the template loader."""
from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf_from_template(template_name: str, context: dict[str, Any]) -> bytes:
    html = render_to_string(template_name, context)
    return HTML(string=html).write_pdf()
```

Services call `render_pdf_from_template` with a Pydantic DTO (`.model_dump()`) as context.

---

## Settings layout

```
config/
├── __init__.py
├── urls.py                # project URL root
├── wsgi.py
├── asgi.py
└── settings/
    ├── __init__.py
    ├── base.py            # everything shared
    ├── dev.py             # extends base; DEBUG=True, SQLite, console email
    └── prod.py            # extends base; DEBUG=False, Postgres, real email, SecurityMiddleware tightened
```

`base.py` skeleton:

```python
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project
    "_shared",
    "usuarios",
    "solicitudes",
    "notificaciones",
    "mentores",
    "reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "_shared.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "_shared.middleware.StructuredLoggingMiddleware",
    "_shared.middleware.AppErrorMiddleware",
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

# Logging configured to include request_id in every record
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

`dev.py` and `prod.py` override only what differs.

---

## URL roots

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("usuarios.urls", namespace="usuarios")),
    path("solicitudes/", include("solicitudes.urls", namespace="solicitudes")),
    path("mentores/", include("mentores.urls", namespace="mentores")),
    path("reportes/", include("reportes.urls", namespace="reportes")),
]
```

```python
# solicitudes/urls.py
from django.urls import include, path

app_name = "solicitudes"

urlpatterns = [
    path("intake/", include("solicitudes.intake.urls", namespace="intake")),
    path("revision/", include("solicitudes.revision.urls", namespace="revision")),
    path("admin-tipos/", include("solicitudes.tipos.urls", namespace="tipos")),
]
```

Each feature owns its own `urls.py` and is included by its app's root.

---

## Base templates

```
templates/
├── base.html                     # site-wide skeleton
├── _shared/
│   └── error.html                # rendered by AppErrorMiddleware
├── components/                   # reusable {% include %} fragments
│   ├── nav.html
│   ├── breadcrumbs.html
│   ├── badge_estado.html
│   ├── form_field.html
│   └── flash_messages.html
└── solicitudes/
    ├── base_solicitudes.html     # optional app-level layout
    ├── intake/
    │   ├── create.html
    │   └── list.html
    └── revision/
        └── detail.html
```

`base.html` provides `{% block title %}`, `{% block content %}`, `{% block extra_css %}`, `{% block extra_js %}`. Optional `base_<app>.html` extends `base.html` to add an app-specific sidebar or breadcrumbs and re-exports the same blocks.

For UI design conventions (Tailwind v4 + Alpine.js + Lucide, shadcn/Vercel monochrome aesthetic, accessibility), see the `frontend-design` skill.

---

## What does NOT belong in `_shared/`

- Anything domain-specific (a solicitudes constant, a mentores helper)
- Anything used by exactly one feature
- Generic name buckets — `utils.py`, `common.py`, `helpers.py` are forbidden
- Business logic of any kind

If you can't write a one-sentence description of a `_shared/` module without using "and" or naming a feature, it doesn't belong here.
