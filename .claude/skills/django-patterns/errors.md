# Errors — Exception Hierarchy + Middleware

The error model is a two-layer hierarchy mirroring the Go `apperror` pattern:

1. **`_shared/exceptions.py`** — base `AppError` and core sentinels every feature can use.
2. **`apps/<app>/<feature>/exceptions.py`** — feature-specific exceptions that subclass the base sentinels.

A single piece of middleware (`_shared/middleware.py`) catches uncaught `AppError` and renders a uniform response. Views catch `AppError` explicitly when they need to surface field-level info to the form; the middleware is the safety net.

---

## `_shared/exceptions.py`

```python
"""Base application exceptions. All domain exceptions inherit from AppError."""
from __future__ import annotations

from typing import Optional


class AppError(Exception):
    """Base for all application-level exceptions.

    Subclasses set:
      - code: machine-readable identifier (snake_case)
      - user_message: Spanish, safe to show end users
      - http_status: HTTP status code the middleware will use
    """
    code: str = "app_error"
    user_message: str = "Ocurrió un error inesperado."
    http_status: int = 500

    def __init__(self, detail: str = "", *, user_message: Optional[str] = None) -> None:
        super().__init__(detail or self.user_message)
        self.detail = detail
        if user_message is not None:
            self.user_message = user_message


class NotFound(AppError):
    code = "not_found"
    user_message = "El recurso solicitado no existe."
    http_status = 404


class Conflict(AppError):
    code = "conflict"
    user_message = "La operación entra en conflicto con el estado actual."
    http_status = 409


class Unauthorized(AppError):
    code = "unauthorized"
    user_message = "No tienes permiso para realizar esta acción."
    http_status = 403


class DomainValidationError(AppError):
    """Domain-level validation that the form layer cannot check.

    Carries field_errors so views can re-display the form with errors attached.
    """
    code = "validation_error"
    user_message = "Los datos no son válidos."
    http_status = 422

    def __init__(
        self,
        detail: str = "",
        *,
        user_message: Optional[str] = None,
        field_errors: Optional[dict[str, list[str]]] = None,
    ) -> None:
        super().__init__(detail, user_message=user_message)
        self.field_errors = field_errors or {}


class ExternalServiceError(AppError):
    code = "external_service_error"
    user_message = "Un servicio externo no está disponible. Intenta más tarde."
    http_status = 502
```

---

## Feature-specific exceptions — examples

```python
# solicitudes/intake/exceptions.py
from _shared.exceptions import Conflict, DomainValidationError, NotFound


class SolicitudNotFound(NotFound):
    code = "solicitud_not_found"
    user_message = "La solicitud no existe o fue eliminada."


class SolicitudAlreadySubmitted(Conflict):
    code = "solicitud_already_submitted"
    user_message = "Esta solicitud ya fue enviada y no puede modificarse."


class InvalidStateTransition(Conflict):
    code = "invalid_state_transition"

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(detail=f"{current} -> {requested}")
        self.current = current
        self.requested = requested
        self.user_message = f"No se puede pasar de {current} a {requested}."
```

```python
# usuarios/auth/exceptions.py
from _shared.exceptions import Unauthorized


class InvalidJWT(Unauthorized):
    code = "invalid_jwt"
    user_message = "Tu sesión expiró. Vuelve a iniciar sesión."


class RoleMismatch(Unauthorized):
    code = "role_mismatch"
    user_message = "Esta sección está disponible solo para personal administrativo."
```

---

## Middleware fallback — `_shared/middleware.py`

```python
"""Middleware that catches uncaught AppError and renders a uniform response."""
from __future__ import annotations

import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from _shared.exceptions import AppError

logger = logging.getLogger(__name__)


class AppErrorMiddleware:
    """Map uncaught AppError to HTTP responses.

    For HTML requests: render an error template with the user_message.
    For AJAX/JSON requests (Accept: application/json or X-Requested-With: XMLHttpRequest):
        return JsonResponse with code, user_message, http_status.

    Views may also catch AppError themselves to surface field_errors to a form.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        if not isinstance(exception, AppError):
            return None  # let Django's default handling kick in

        logger.warning(
            "AppError reached middleware",
            extra={
                "code": exception.code,
                "detail": exception.detail,
                "path": request.path,
                "method": request.method,
                "user_id": getattr(request.user, "id", None),
            },
        )

        if self._wants_json(request):
            return JsonResponse(
                {
                    "error": {
                        "code": exception.code,
                        "message": exception.user_message,
                    }
                },
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

Register it in `config/settings/base.py`:

```python
MIDDLEWARE = [
    # ... Django defaults ...
    "_shared.middleware.AppErrorMiddleware",
]
```

---

## View-level handling — when to catch vs let it bubble

**Let the middleware handle it (default):**

```python
def post(self, request):
    service = get_solicitud_service()
    detail = service.create(input_dto)  # if this raises AppError, middleware catches
    return redirect(...)
```

**Catch when you need form context:**

```python
def post(self, request):
    form = CreateSolicitudForm(request.POST)
    if not form.is_valid():
        return render(request, self.template_name, {"form": form}, status=400)

    try:
        detail = service.create(input_dto)
    except DomainValidationError as e:
        # Surface field errors back into the form
        for field, errors in e.field_errors.items():
            for err in errors:
                form.add_error(field, err)
        return render(request, self.template_name, {"form": form}, status=e.http_status)
    except AppError as e:
        # Other domain errors: render a flash message and redisplay
        messages.error(request, e.user_message)
        return render(request, self.template_name, {"form": form}, status=e.http_status)

    return redirect(...)
```

---

## Rules

1. **Repositories raise feature-specific exceptions, never Django's.**
   ```python
   try:
       row = Solicitud.objects.get(folio=folio)
   except Solicitud.DoesNotExist:
       raise SolicitudNotFound(folio)
   ```

2. **Services raise feature exceptions for domain rule violations.** They never raise generic `Exception` or `RuntimeError`.

3. **Views catch `AppError` selectively.** If the only thing to do is render an error page, let the middleware handle it. Catch when you have form-aware context to add.

4. **Middleware catches everything that escaped.** Logged with the request ID; user gets a clean error page or JSON.

5. **Never bare `except:` in services or views.** That would swallow real bugs. The middleware fallback exists for the unexpected.

6. **Don't catch `AppError` to log and re-raise.** The middleware logs centrally; double-logging just creates noise.

7. **HTTP-level errors (404 for "URL not found")** are still Django's job. `AppError` is for domain errors that happen *inside* a handled view.
