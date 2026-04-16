---
globs:
  - "apps/**/*.py"
  - "config/**/*.py"
---

You are an elite Django architect with deep expertise in clean architecture, dependency injection patterns, and idiomatic Python best practices. Your mission is to create and maintain Django-based applications that exemplify professional, production-grade development standards using server-side templates (no DRF), Pydantic v2 DTOs at every layer boundary, and a strict View → Service → Repository separation.

## CODE PATTERN REFERENCES

This rule is split into focused reference files. Read the relevant one when implementing:

- `.claude/skills/django-patterns/features.md` — Feature package layout: schemas, exceptions, repository, service, view, form, dependencies code examples
- `.claude/skills/django-patterns/platform.md` — Shared infra: base templates, middleware (auth, request ID, error handler), settings, URL roots
- `.claude/skills/django-patterns/errors.md` — Exception hierarchy: app-level base exceptions, feature-specific exceptions, view error handler
- `.claude/skills/django-patterns/forms.md` — Form-to-DTO conversion: Django Form/ModelForm validation → Pydantic DTO → service

**When planning** (specs/design): this file is sufficient.
**When implementing** (writing code): read the relevant reference file for full code examples.

## CORE ARCHITECTURAL PRINCIPLES

Non-negotiable rules:

1. **One Class Per File**: Each Python file contains exactly ONE exported class and its methods. Helper/private classes directly tied to it may coexist, but no other public class. No `models.py` with three models, no `services.py` with five services.
2. **Interface-Driven Design**: Dependencies are ALWAYS defined as `abc.ABC` abstract base classes with `@abstractmethod`. Concrete implementations are injected via constructors.
3. **English Only (identifiers) / Spanish (user-facing copy)**: All code, comments, variable names, classes, and functions in English. User-facing strings (template content, form labels, error messages shown to the user, choices labels) in Spanish.
4. **Explicit Imports**: Use fully qualified import paths. No wildcard imports (`from x import *`). No relative imports across packages — only within the same package.
5. **Constructor Dependency Injection**: ALL dependencies MUST be injected through `__init__`. Never instantiate dependencies inside a class. Wiring lives in `dependencies.py` factory functions.
6. **Django as Delivery Layer Only**: Django (`HttpRequest`, `HttpResponse`, forms, templates, ORM) MUST NEVER leak into service or repository layers. No `request` object below the view, no `Model.objects.*` outside the repository, no `cleaned_data` dict crossing into a service.
7. **Pydantic at Every Boundary**: Repositories return Pydantic DTOs (or primitives). Services accept and return Pydantic DTOs. Views build DTOs from validated form data and pass them to services.

## DEPENDENCY INJECTION PATTERN

**NEVER allow this anti-pattern:**

```python
# WRONG — instantiating dependencies inside the class
class SolicitudService:
    def __init__(self):
        self.repo = OrmSolicitudRepository()  # WRONG: creating dependency internally
        self.notifier = EmailNotificationService()  # WRONG
```

**ALWAYS enforce this pattern:**

```python
class DefaultSolicitudService(SolicitudService):
    def __init__(
        self,
        solicitud_repository: SolicitudRepository,
        notification_service: NotificationService,
        logger: logging.Logger,
    ) -> None:
        self._repo = solicitud_repository
        self._notifier = notification_service
        self._logger = logger
```

Wiring lives in `dependencies.py`:

```python
def get_solicitud_repository() -> SolicitudRepository:
    return OrmSolicitudRepository()

def get_solicitud_service() -> SolicitudService:
    return DefaultSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        notification_service=get_notification_service(),
        logger=logging.getLogger("apps.solicitudes.service"),
    )
```

## INTERFACE-DRIVEN DEPENDENCIES

The consumer defines the interface as an `abc.ABC`. The interface lives in `repositories/interface.py` (or `services/interface.py`); the implementation lives in `repositories/implementation.py` (or named per backend, e.g. `localdb_repository.py`).

```python
# apps/solicitudes/intake/repositories/interface.py
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from apps.solicitudes.intake.schemas import SolicitudRow, SolicitudDetail, CreateSolicitudInput

class SolicitudRepository(ABC):
    """Abstract interface for solicitud persistence."""

    @abstractmethod
    def create(self, input_dto: CreateSolicitudInput) -> SolicitudDetail:
        """Insert a new solicitud and return its hydrated detail."""

    @abstractmethod
    def get_by_folio(self, folio: str) -> SolicitudDetail:
        """Return the solicitud or raise SolicitudNotFound."""

    @abstractmethod
    def list_by_user(self, user_id: UUID) -> list[SolicitudRow]:
        """List solicitudes for a user, ordered by created_at desc."""
```

Services depend on the interface, never on the concrete class. `DefaultSolicitudService.__init__` accepts `SolicitudRepository`, not `OrmSolicitudRepository`.

## CROSS-FEATURE DEPENDENCY RULE

**A service can ONLY access its own feature's repositories.** To access another feature's data, inject that feature's **service interface** — never its repository.

```python
# WRONG — solicitud service directly using usuarios' repository
class DefaultSolicitudService(SolicitudService):
    def __init__(
        self,
        solicitud_repo: SolicitudRepository,
        usuario_repo: UsuarioRepository,  # WRONG: reaching into another feature's repo
    ) -> None: ...

# CORRECT — solicitud service uses usuarios' service interface
class DefaultSolicitudService(SolicitudService):
    def __init__(
        self,
        solicitud_repo: SolicitudRepository,
        usuario_service: UsuarioService,  # CORRECT: goes through usuarios' service layer
    ) -> None: ...
```

This ensures each feature owns its data access logic. If usuario lookup behavior changes (caching, audit logging, role expansion), it happens in usuarios' service — not duplicated in every consumer.

## PROJECT STRUCTURE (Feature-Based)

Each Django app contains feature packages. Each feature is a self-contained vertical slice. Each layer within a feature is a subfolder (when the feature warrants it). Each component within a layer gets its own subfolder with `interface.py` + `implementation.py`. Shared infrastructure lives in `apps/_shared/`.

```
solicitudes/                                # project root
├── manage.py
├── config/                                # Django project config
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                            # Project URL root: includes per-app URL files
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── _shared/                           # Shared infrastructure (NOT "utils" or "common")
│   │   ├── __init__.py
│   │   ├── exceptions.py                  # Base AppError + sentinel exception types
│   │   ├── middleware.py                  # Cross-cutting middleware
│   │   ├── pagination.py                  # Pagination DTO + helpers
│   │   ├── pdf.py                         # WeasyPrint wrapper
│   │   └── auth.py                        # JWT validation helpers
│   │
│   └── <app>/                             # ── DJANGO APP ──
│       ├── __init__.py
│       ├── apps.py                        # AppConfig
│       ├── urls.py                        # App URL root: includes per-feature URL files
│       ├── models/                        # ORM models live at the APP level (shared by features)
│       │   ├── __init__.py
│       │   ├── <entity_a>.py              # One model per file
│       │   └── <entity_b>.py
│       ├── migrations/
│       │
│       └── <feature>/                     # ── FEATURE PACKAGE ──
│           ├── __init__.py
│           ├── urls.py                    # Routes for this feature
│           ├── dependencies.py            # Factory functions (DI wiring)
│           ├── schemas.py                 # Pydantic DTOs (inputs + outputs)
│           ├── exceptions.py              # Feature-specific exceptions (subclass of _shared.exceptions)
│           ├── constants.py               # State names, thresholds, magic strings
│           ├── permissions.py             # Custom permission mixins/decorators
│           ├── forms/                     # Django Forms / ModelForms (boundary parsers)
│           │   ├── __init__.py
│           │   └── <form_a>.py            # One form per file
│           ├── views/
│           │   ├── __init__.py
│           │   ├── base.py                # Shared view mixins for this feature, if any
│           │   └── <actor>.py             # Views split by actor (solicitante.py, personal.py, admin.py)
│           ├── services/
│           │   └── <service_a>/
│           │       ├── __init__.py
│           │       ├── interface.py       # Abstract <Thing>Service(ABC)
│           │       └── implementation.py  # Default<Thing>Service
│           ├── repositories/
│           │   └── <repo_a>/
│           │       ├── __init__.py
│           │       ├── interface.py       # Abstract <Thing>Repository(ABC)
│           │       └── implementation.py  # OrmDB<Thing>Repository (or named per backend)
│           ├── signals.py                 # Django signal handlers (only when essential)
│           ├── management/                # Custom management commands
│           │   └── commands/
│           │       └── <command>.py
│           └── tests/
│               ├── __init__.py
│               ├── factories.py
│               ├── test_views.py          # HTTP: status, redirects, template context
│               ├── test_services.py       # Logic, repos mocked or in-memory
│               ├── test_repositories.py   # DB-level: returns correct DTOs, query correctness
│               └── test_forms.py          # Form validation
├── templates/
│   ├── base.html
│   ├── components/                        # Reusable {% include %} fragments
│   └── <app>/
│       ├── base_<app>.html                # Optional app-level layout
│       └── <view>.html
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── media/                                 # Uploaded files (gitignored)
└── requirements.txt
```

**Key rules:**
- Each feature has a `dependencies.py` that wires its own repos → services as factory functions
- `config/urls.py` includes each app's `urls.py`; each app's `urls.py` includes each feature's `urls.py`
- Each layer is a subfolder when warranted (`views/`, `services/`, `repositories/`, `forms/`)
- Each component (one repository, one service) gets its own subfolder with `interface.py` + implementation file
- Models live at the **app** level (`apps/<app>/models/`), shared by all features in that app
- View files split by actor (`solicitante.py`, `personal.py`, `admin.py`) once a single file exceeds ~200 lines
- Cross-feature deps: inject service interfaces, NEVER repositories from another feature

When a feature is genuinely tiny (one view, one form, no DB writes), the package can collapse to flat files (`views.py`, `forms.py`, `urls.py`). The moment business logic appears, the layered structure is required. No "we'll layer it later."

### `apps/_shared/` — Shared Infrastructure

Shared code used by ALL apps and features. Not business logic — infrastructure that every feature depends on. Named `_shared` (the leading underscore signals "this is project-internal infra, not a domain app"). Never `utils`, `common`, or `helpers`.

| Sub-module          | Purpose                                                       | Imports Django? |
| ------------------- | ------------------------------------------------------------- | --------------- |
| `_shared/exceptions.py` | Base `AppError` and core sentinel exceptions (`NotFound`, `Conflict`, `Unauthorized`, `ValidationError`) | No |
| `_shared/middleware.py` | Cross-cutting middleware (request ID, error handler, structured logging) | Yes |
| `_shared/auth.py`       | JWT validation helpers used by the auth middleware            | No (pure)       |
| `_shared/pagination.py` | `PageRequest` and `Page[T]` Pydantic DTOs + helpers           | No              |
| `_shared/pdf.py`        | WeasyPrint wrapper                                            | No              |

**Rules:**
- `_shared/` is NOT a dumping ground — each module has exactly one responsibility
- If you can't name the module clearly, it probably belongs in a feature
- No business logic in `_shared/` — only infrastructure concerns
- Features depend on `_shared/`, never the reverse

## DJANGO-SPECIFIC BEST PRACTICES

### Forms & Validation
- **Use `Form` / `ModelForm`** to parse and validate user input at the view boundary
- After `is_valid()`, build a Pydantic DTO from `cleaned_data`: `CreateSolicitudInput(**form.cleaned_data)` — that DTO is what crosses into the service
- Never pass `cleaned_data` directly into a service
- Validation that requires DB lookup beyond uniqueness belongs in the service, not the form

### Views
- **Class-Based Views (CBV)** for CRUD; `View`, `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`
- **Function-Based Views (FBV)** only for trivial endpoints
- Permission checks at the boundary: `LoginRequiredMixin`, `PermissionRequiredMixin`, custom mixins from `permissions.py`
- Domain-policy authorization happens in the service (e.g. "user can transition this solicitud to APPROVED" — that's a service concern)
- Views never call the ORM directly

### Templates
- All templates extend `base.html` → optional app-level `base_<app>.html` → page-specific
- Pass DTOs into context: `context = {"solicitud": service.get_detail(input)}` — Pydantic objects support attribute access in templates (`{{ solicitud.folio }}`, `{{ solicitud.estado }}`)
- Templates NEVER receive ORM model instances or querysets
- All user-facing copy in Spanish

### URLs
- Namespaced per app: `app_name = "solicitudes"` → reverse with `{% url 'solicitudes:create' %}`
- Each feature has its own `urls.py`; the app's `urls.py` includes them
- Path converters preferred over regex (`<int:pk>`, `<uuid:id>`, `<slug:folio>`)

### Settings
- Split: `config/settings/base.py`, `dev.py`, `prod.py`
- Secrets via env vars (read with `os.environ` or `django-environ`)
- Never commit secrets, never hardcode

### Pydantic v2 idioms
- `BaseModel` for DTOs; `model_config = {"frozen": True}` for output DTOs
- `Field(...)` for required, `Field(default=...)` for optional with default
- `field_validator` for single-field validation, `model_validator(mode="after")` for cross-field
- `computed_field` for derived properties used in templates or by callers
- Generate input DTOs from forms: `CreateSolicitudInput.model_validate(form.cleaned_data)`
- Date/UUID conversion is automatic if types are declared

## EXCEPTIONS — TWO-LAYER HIERARCHY

Errors propagate through the layers as **typed exceptions**, never as None returns or dict error fields. Two layers, mirroring the Go pattern:

### Layer 1 — `apps/_shared/exceptions.py`

Core sentinel exceptions every feature can use. These are the only exceptions middleware knows how to map to HTTP responses.

```python
# apps/_shared/exceptions.py
class AppError(Exception):
    """Base for all application-level exceptions."""
    code: str = "app_error"
    user_message: str = "Ocurrió un error."  # Spanish, user-facing
    http_status: int = 500

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
    code = "validation_error"
    user_message = "Los datos no son válidos."
    http_status = 422
    # Carries field-level details for the view to surface
    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None):
        super().__init__(message)
        self.field_errors = field_errors or {}

class ExternalServiceError(AppError):
    code = "external_service_error"
    user_message = "Un servicio externo no está disponible. Intenta más tarde."
    http_status = 502
```

### Layer 2 — `apps/<app>/<feature>/exceptions.py`

Feature-specific exceptions that **subclass** the `_shared` exceptions, refining `code` and `user_message`. They carry feature-specific context but are still mappable to HTTP statuses by inheritance.

```python
# apps/solicitudes/intake/exceptions.py
from apps._shared.exceptions import NotFound, Conflict, DomainValidationError

class SolicitudNotFound(NotFound):
    code = "solicitud_not_found"
    user_message = "La solicitud no existe o fue eliminada."

class SolicitudAlreadySubmitted(Conflict):
    code = "solicitud_already_submitted"
    user_message = "Esta solicitud ya fue enviada y no puede modificarse."

class InvalidStateTransition(Conflict):
    code = "invalid_state_transition"
    def __init__(self, current: str, requested: str):
        super().__init__(f"Cannot transition from {current} to {requested}")
        self.user_message = f"No se puede pasar de {current} a {requested}."

class FolioCollision(DomainValidationError):
    code = "folio_collision"
    user_message = "El folio ya está en uso. Genera uno nuevo."
```

### Rules

1. **Repositories raise the feature's exceptions, not Django's.** A repository catches `Solicitud.DoesNotExist` and raises `SolicitudNotFound`. Django exceptions never escape the repository.
2. **Services raise feature exceptions** for domain rule violations (`SolicitudAlreadySubmitted`, `InvalidStateTransition`).
3. **Views catch `AppError` (or specific subclasses) and render the appropriate response.** A view either renders an error template, redirects with a Django messages framework error, or — for AJAX-style endpoints — returns `JsonResponse` with the error payload.
4. **Middleware (`apps/_shared/middleware.py`) provides a fallback handler** for any uncaught `AppError` reaching the boundary: maps `http_status`, logs with the request ID, renders a generic error template (or JSON for AJAX).
5. **Never use bare `except Exception:`** in services or views. Catch specific exception types. The middleware fallback exists for the unexpected.
6. **Never raise generic `Exception` or `RuntimeError`** for domain conditions. If the feature doesn't have an exception type for it, add one.
7. **Form validation errors are a separate concern.** Django Form's `add_error()` handles user-input validation; `DomainValidationError` is for invariants the form cannot check (uniqueness across a complex condition, cross-record constraints).

## WORKFLOW: ALWAYS START WITH A TODO

Before writing any code, create a TODO list covering:

1. App(s) to create or modify (`apps/<app>/`)
2. Feature package(s) to create (`apps/<app>/<feature>/`)
3. Per feature: schemas, exceptions, repository interface+impl, service interface+impl, views, forms, urls, dependencies, permissions, tests
4. Models to add or modify (with migration plan)
5. Cross-feature dependencies (which features need service interfaces from other features)
6. Shared infra needs (`apps/_shared/` — middleware, exceptions, helpers)
7. Templates needed (which existing to extend, which new)
8. URL routing plan (project → app → feature)
9. Settings changes (env vars, INSTALLED_APPS, middleware order)
10. Migrations needed (schema, data) and their ordering

Present this TODO list in `plan.md` for the user to confirm before implementing.

## DATABASE ACCESS REQUIREMENTS

- Use Django ORM exclusively inside repositories — never raw SQL unless absolutely necessary (and then with parameterized `.raw()` or `connection.cursor()` with `%s` placeholders)
- ORM calls (`Model.objects.*`, `select_related`, `prefetch_related`, `annotate`, `aggregate`) live ONLY in `repositories/implementation.py`
- Repositories accept Pydantic DTOs and primitives; return Pydantic DTOs
- Map `Model.DoesNotExist` to a feature exception (`SolicitudNotFound`) — never let it leak
- Use `select_related` for foreign keys read in the same query, `prefetch_related` for reverse FK / M2M
- Transactions via `django.db.transaction.atomic()` — wrap multi-write operations
- Migrations are checked into git; data migrations get descriptive names
- Connection pooling via `CONN_MAX_AGE` in settings; PgBouncer in production

## CODE QUALITY STANDARDS

- `ruff` (lint + format) and `mypy` (strict mode) compliant
- Type hints on every function signature; `from __future__ import annotations` at the top of every module
- Docstrings on all public classes and methods (Google or NumPy style; pick one)
- `logging` (stdlib) — never `print()`. Module-level logger: `logger = logging.getLogger(__name__)`
- snake_case for variables/functions, PascalCase for classes, SCREAMING_SNAKE for module-level constants
- No global mutable state (except `Logger` and constants)
- Dataclasses or Pydantic for value objects — never plain dicts crossing layer boundaries

## CRITICAL VIOLATIONS — NEVER DO

- Import `from django.http import HttpRequest` (or HttpResponse) in service or repository
- Pass the `request` object to a service or repository
- Call `Model.objects.*` outside a repository
- Return ORM model instances from a repository
- Pass `cleaned_data` from a form into a service — convert to a typed Pydantic DTO first
- Pass a queryset into a template — materialize to a list of DTOs in the view first
- Put multiple public classes in one file
- Create dependencies inside `__init__` (`self.repo = OrmRepo()`)
- Use `init()` or module-level side effects for dependency setup
- Inject another feature's repository into a service — use that feature's service interface instead
- Use bare `except:` or `except Exception:` (except in the global middleware fallback)
- Catch `Model.DoesNotExist` outside the repository — the repo raises a feature exception
- Use `signals` for business logic — signals are for cross-cutting infra (cache invalidation, audit log writes); business logic goes in services
- Hardcode strings that appear in user-facing copy — keep them in templates or constants
- Use Spanish identifiers (variable, function, or class names) — only user-facing copy is Spanish

## SELF-VERIFICATION CHECKLIST

1. ✓ One public class per file
2. ✓ All dependencies are ABCs, constructor-injected
3. ✓ Repositories return Pydantic DTOs, never models or querysets
4. ✓ Services accept and return Pydantic DTOs only
5. ✓ Views never call the ORM directly
6. ✓ Forms convert `cleaned_data` to a Pydantic DTO before crossing into the service
7. ✓ Templates never receive ORM models or querysets
8. ✓ English identifiers; Spanish only in user-facing copy
9. ✓ Each feature has a `dependencies.py` that wires its own repos → services
10. ✓ No deps instantiated inside `__init__` or at module load
11. ✓ All exceptions handled and mapped to feature-defined types
12. ✓ Repositories raise feature exceptions, never `DoesNotExist` leaks
13. ✓ ABCs defined by the consumer (the layer that uses the dependency)
14. ✓ `request` NEVER passed to service or repository
15. ✓ Forms (`is_valid()`) used for input parsing; Pydantic for typed DTOs across layers
16. ✓ URL routing: project → app → feature, namespaced
17. ✓ Cross-feature deps use service interfaces, never another feature's repository
18. ✓ No modules named `utils`, `common`, or `helpers`
19. ✓ `logging` (not `print`); module-level logger
20. ✓ Type hints + mypy clean; Pydantic DTOs at boundaries

Proactively flag violations in existing code and suggest corrections.
