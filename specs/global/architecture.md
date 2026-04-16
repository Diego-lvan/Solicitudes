# Architecture — Sistema de Solicitudes

> **Canonical architectural rules:** `.claude/rules/django-code-architect.md`. **Test rules:** `.claude/rules/django-test-architect.md`. **Code examples:** `.claude/skills/django-patterns/`. This document gives the high-level shape; consult those for layer-by-layer detail.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Framework | Django 5.x (server-side templates, no DRF) |
| DTOs | Pydantic v2 (every layer boundary) |
| Rendering | Django Templates + Bootstrap 5 |
| Database | PostgreSQL (prod) / SQLite (dev) via Django ORM (contained in repositories) |
| PDF Generation | WeasyPrint |
| Async Tasks | Celery + Redis (emails) |
| File Storage | Local filesystem (`media/`) for dev; pluggable in prod |
| Auth | JWT validation middleware (external provider) |
| Tests | `pytest` + `pytest-django`, `model_bakery`, `freezegun`, `responses` |

## Architectural Style

**View → Service → Repository**, with Pydantic v2 DTOs at every boundary. The Django ORM never escapes the repository layer. Services are pure-Python business logic. Views own HTTP concerns and template rendering. Forms parse user input and convert `cleaned_data` to typed Pydantic DTOs before crossing into the service. Custom exceptions inherit from `apps._shared.exceptions.AppError` and are mapped to HTTP responses by middleware.

```
HTTP Request
   │
   ▼
View (HTTP boundary)  ── Form (parse + validate) ── DTO ──▶
   │                                                       │
   ▼                                                       │
Service (business logic, ABC + impl)                       │
   │                                                       │
   ▼                                                       │
Repository (ORM-only, ABC + impl) ──▶ DTO ◀────────────────┘
   │
   ▼
Django ORM / Postgres
```

## Project Layout

```
solicitudes/
├── specs/                    # SDD specs (source of truth)
├── config/                   # Django project config
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── _shared/              # Cross-cutting infra (exceptions, middleware, auth, pagination, pdf)
│   ├── usuarios/             # Auth, user model, roles, profile
│   ├── solicitudes/          # Core: tipos, formularios, lifecycle, archivos, pdf
│   ├── notificaciones/       # Email dispatch, preferences
│   ├── mentores/             # Mentor catalog and assignments
│   └── reportes/             # Dashboards and exports
├── templates/                # base.html + components/ + per-app
├── static/                   # css, js, img
├── media/                    # Uploaded files (gitignored)
├── locale/                   # i18n (es_MX)
├── manage.py
└── requirements.txt
```

Each Django app is a layered vertical slice. Within an app, each feature is its own package:

```
apps/<app>/<feature>/
├── schemas.py                # Pydantic DTOs
├── exceptions.py             # Feature-specific exceptions (subclass _shared.exceptions)
├── repositories/<x>/{interface,implementation}.py
├── services/<x>/{interface,implementation}.py
├── views/<actor>.py          # solicitante.py, personal.py, admin.py
├── forms/                    # one form per file
├── dependencies.py           # DI factory functions
├── permissions.py            # custom mixins/decorators
├── constants.py
├── urls.py
└── tests/                    # test_views, test_services, test_repositories, test_forms
```

ORM models live at the **app** level (`apps/<app>/models/`), one per file, shared by all features in that app. Repositories from any feature import models from the app's `models/` package.

## App Responsibilities

### `_shared`
Cross-cutting infrastructure. **No domain logic.**
- `exceptions.py` — `AppError` base + sentinels (`NotFound`, `Conflict`, `Unauthorized`, `DomainValidationError`, `ExternalServiceError`)
- `middleware.py` — `RequestIDMiddleware`, `StructuredLoggingMiddleware`, `AppErrorMiddleware`
- `auth.py` — JWT validation helpers (pure-Python, no `HttpRequest` dependency)
- `pagination.py` — `PageRequest` and `Page[T]` DTOs
- `pdf.py` — WeasyPrint wrapper

### `usuarios`
- JWT validation middleware (uses `_shared/auth.py`)
- Custom User model (extension of `AbstractUser`)
- Role catalog (alumno, docente, personal, admin)
- Profile data + permission mixins
- No login/register views — auth is external

### `solicitudes` (core)
Multiple features:
- **`tipos`** — TipoSolicitud catalog with dynamic field schema (FieldDefinition)
- **`intake`** — Solicitante creates a draft, fills the dynamic form, submits
- **`revision`** — Personal reviews, approves, or rejects with observations
- **`lifecycle`** — State machine (BORRADOR → PENDIENTE → APROBADA / RECHAZADA / CANCELADA), folio generation
- **`archivos`** — Attachment uploads (validated by extension/size) and downloads (permission-checked)
- **`pdf`** — WeasyPrint rendering of approved solicitudes from per-tipo templates

### `notificaciones`
- Email dispatch on state transitions (Celery + Redis async; sync fallback)
- Per-user notification preferences
- Templated emails with the solicitud snapshot
- Failure-tolerant — SMTP down does not block transitions

### `mentores`
- Mentor catalog (matrícula, activo, fecha_alta)
- Mentor-user assignment relations
- Admin CRUD (list, add manually, bulk import via CSV)
- Service: `is_mentor(matricula)` consumed by other features through its service interface

### `reportes`
- Aggregated metrics (solicitudes by estado, tipo, periodo)
- CSV / Excel export
- Role-scoped dashboard views

## Key Patterns

### Authentication
```
HTTP Request
  → RequestIDMiddleware (assigns request_id)
  → JWT middleware (apps.usuarios) — validates via apps._shared.auth.decode_jwt
                                   — sets request.user
                                   — invalid/expired → 401 redirect to external login
  → View (LoginRequiredMixin / role mixins enforce access)
  → Service (domain-policy authorization, e.g. owner-only edit)
```

### Dynamic forms (intake)
```
TipoSolicitud → [FieldDefinition...] → DynamicForm (built at runtime by intake.forms)
                                     → cleaned_data
                                     → CreateSolicitudInput (Pydantic)
                                     → SolicitudService.create
                                     → SolicitudRepository.create  ── stores ValorCampo per field
```

### State machine
```
Solicitud.estado: BORRADOR → PENDIENTE → APROBADA
                                       → RECHAZADA
                  BORRADOR → CANCELADA
                  PENDIENTE → CANCELADA

Forbidden transitions raise InvalidStateTransition(current, requested).
Each successful transition emits a Notification (apps.notificaciones service).
```

### Cross-app dependency rule
A service can only access its own feature's repositories. To read another feature's data, inject that feature's **service interface**, never its repository. Example: `notificaciones.dispatch_service` consumes `usuarios.UserService` (not `UserRepository`) to fetch the recipient's email and preferences.

### Error flow
```
Service raises feature exception (subclass of AppError)
  → bubbles up
  → AppErrorMiddleware catches in process_exception
  → maps http_status, logs with request_id
  → renders _shared/error.html OR returns JSON for AJAX requests
```

Views may catch `AppError` selectively to surface `field_errors` back into the form (re-render with error markup attached). The middleware is the safety net.

### File organization
```
media/solicitudes/{folio}/
├── campo_{id}_archivo.pdf
├── comprobante_pago.pdf
└── ...
```
Service writes through a storage abstraction; repository never touches the filesystem directly.

## Conventions

- **One public class per file** — no `models.py` with three models, no `services.py` with five services
- **English** for code identifiers; **Spanish** for user-facing copy (templates, form labels, choices labels, exception `user_message`)
- **Type hints everywhere**; `mypy --strict` clean
- **Pydantic v2** for DTOs, dataclasses for value objects, never bare dicts crossing layers
- **Tests** in `apps/<app>/<feature>/tests/`; one file per layer (`test_views.py`, `test_services.py`, `test_repositories.py`, `test_forms.py`)
- **Settings split:** `config/settings/base.py` + `dev.py` + `prod.py`; secrets via env vars
- **URL routing:** project → app → feature, namespaced (`{% url 'solicitudes:intake:create' %}`)
- **Tests**: `pytest` + `pytest-django`, NOT `manage.py test`. Repositories tested against real DB; services tested with in-memory fake repositories

## What this document is NOT

- It does not list specific endpoints, DDL, or code patterns. Those live in `plan.md` per initiative (in flight) and in per-feature `design.md` (after completion).
- It does not list deprecated code paths. The old code under `code_example/` is reference material; new code follows this architecture.

## Related Specs

- `.claude/rules/django-code-architect.md` — canonical architectural rules
- `.claude/rules/django-test-architect.md` — test conventions
- `specs/shared/infrastructure/` — `_shared/` deep specs (filled after initiative 001)
- `specs/shared/best-practices/` — cross-cutting practices (filled after initiative 001)
- `specs/flows/` — cross-app data flows (filled as initiatives create them)
